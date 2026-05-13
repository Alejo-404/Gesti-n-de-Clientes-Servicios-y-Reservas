# ============================================================
# INTERFAZ GRÁFICA — Sistema de Gestión de Clientes, Servicios y Reservas
# Ejecutar con: python interfaz_sistema.py
# ============================================================
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, font as tkfont
from abc import ABC, abstractmethod
from datetime import datetime
import re
import sys
import io
import os
import threading


# ═══════════════════════════════════════════════════════════
# NÚCLEO DEL SISTEMA (lógica de negocio)
# ═══════════════════════════════════════════════════════════

LOG_FILE = "interfaz_sistema.log"


class Logger:
    @staticmethod
    def registrar(nivel: str, mensaje: str):
        try:
            ts    = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            linea = f"[{nivel.upper():<8}] {ts} | {mensaje}\n"
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(linea)
        except OSError:
            pass

    @classmethod
    def info(cls, m):    cls.registrar("INFO",    m)
    @classmethod
    def error(cls, m):   cls.registrar("ERROR",   m)
    @classmethod
    def warn(cls, m):    cls.registrar("WARNING", m)
    @classmethod
    def critico(cls, m): cls.registrar("CRITICO", m)


# ── Excepciones ──────────────────────────────────────────────
class ErrorSistema(Exception):
    def __init__(self, msg: str, codigo: str = "E000"):
        super().__init__(msg)
        self.codigo = codigo
        Logger.error(f"[{codigo}] {msg}")


class DatoInvalidoError(ErrorSistema):
    def __init__(self, campo: str, valor=None):
        extra = f": '{valor}'" if valor is not None else ""
        super().__init__(f"Dato inválido en '{campo}'{extra}", "E001")
        self.campo = campo


class ParametroFaltanteError(ErrorSistema):
    def __init__(self, param: str):
        super().__init__(f"Parámetro faltante: '{param}'", "E002")


class ServicioNoDisponibleError(ErrorSistema):
    def __init__(self, nombre: str):
        super().__init__(f"Servicio no disponible: '{nombre}'", "E003")


class ReservaInvalidaError(ErrorSistema):
    def __init__(self, motivo: str):
        super().__init__(f"Reserva inválida: {motivo}", "E004")


class OperacionNoPermitidaError(ErrorSistema):
    def __init__(self, op: str, estado: str):
        super().__init__(f"Operación '{op}' no permitida. Estado: '{estado}'", "E005")


class CalculoInconsistenteError(ErrorSistema):
    def __init__(self, detalle: str):
        super().__init__(f"Cálculo inconsistente: {detalle}", "E006")


class ValidacionFallidaError(ErrorSistema):
    def __init__(self, regla: str, valor=None):
        msg = f"Regla incumplida: {regla}" + (f" (valor={valor})" if valor is not None else "")
        super().__init__(msg, "E007")
        self.regla = regla


# ── Validadores ──────────────────────────────────────────────
class Validador(ABC):
    @abstractmethod
    def validar(self, datos: dict) -> list:
        pass

    def es_valido(self, datos: dict) -> bool:
        return len(self.validar(datos)) == 0


class ValidadorCliente(Validador):
    _RE_CORREO    = re.compile(r"^[\w\.\-]+@[\w\.\-]+\.\w{2,}$")
    _RE_DOCUMENTO = re.compile(r"^\d{7,12}$")

    def validar(self, datos: dict) -> list:
        errores = []
        n = str(datos.get("nombre", "")).strip()
        if not n:                      errores.append("Nombre vacío")
        elif len(n) < 3:               errores.append(f"Nombre muy corto: '{n}'")
        elif len(n) > 100:             errores.append("Nombre > 100 caracteres")

        d = str(datos.get("documento", ""))
        if not self._RE_DOCUMENTO.match(d):
            errores.append(f"Documento inválido: '{d}' (7-12 dígitos)")

        c = str(datos.get("correo", ""))
        if not self._RE_CORREO.match(c):
            errores.append(f"Correo inválido: '{c}'")
        return errores


class ValidadorServicio(Validador):
    TIPOS   = {"ReservaSala", "AlquilerEquipo", "Asesoria"}
    P_MIN   = 1_000
    P_MAX   = 10_000_000

    def validar(self, datos: dict) -> list:
        errores = []
        n = str(datos.get("nombre", "")).strip()
        if not n:         errores.append("Nombre del servicio vacío")
        elif len(n) > 80: errores.append("Nombre > 80 caracteres")

        try:
            p = float(datos.get("precio_base", 0))
            if p < self.P_MIN: errores.append(f"Precio muy bajo: ${p:,.0f}")
            if p > self.P_MAX: errores.append(f"Precio excesivo: ${p:,.0f}")
        except (TypeError, ValueError):
            errores.append(f"Precio no numérico: '{datos.get('precio_base')}'")

        t = datos.get("tipo", "")
        if t and t not in self.TIPOS:
            errores.append(f"Tipo inválido: '{t}'")
        return errores


class ValidadorReserva(Validador):
    def validar(self, datos: dict) -> list:
        errores = []
        dur = datos.get("duracion")
        if dur is None:
            errores.append("Duración no especificada")
        else:
            try:
                dur = int(dur)
                if dur < 1:  errores.append(f"Duración mínima 1h (recibido: {dur})")
                if dur > 24: errores.append(f"Duración máxima 24h (recibido: {dur})")
            except (TypeError, ValueError):
                errores.append(f"Duración no entera: '{dur}'")

        if not isinstance(datos.get("cliente_id"), int) or datos["cliente_id"] <= 0:
            errores.append(f"ID cliente inválido: '{datos.get('cliente_id')}'")
        if not isinstance(datos.get("servicio_id"), int) or datos["servicio_id"] <= 0:
            errores.append(f"ID servicio inválido: '{datos.get('servicio_id')}'")
        if not datos.get("servicio_disponible", True):
            errores.append("Servicio no disponible")
        return errores


class ValidadorCalculo(Validador):
    def validar(self, datos: dict) -> list:
        errores = []
        try:
            t = float(datos.get("tasa_impuesto", 0))
            if not (0 <= t <= 1): errores.append(f"Tasa fuera de [0-1]: {t}")
        except (TypeError, ValueError):
            errores.append(f"Tasa no numérica")

        try:
            d = float(datos.get("descuento", 0))
            if d < 0: errores.append(f"Descuento negativo: {d}")
            b = datos.get("costo_base")
            if b is not None and d > float(b):
                errores.append(f"Descuento (${d:,.0f}) > base (${float(b):,.0f})")
        except (TypeError, ValueError):
            errores.append("Descuento no numérico")
        return errores


# ── Entidades ────────────────────────────────────────────────
class Entidad(ABC):
    def __init__(self, id: int):
        if not isinstance(id, int) or id <= 0:
            raise DatoInvalidoError("id", id)
        self._id = id

    def get_id(self) -> int: return self._id

    @abstractmethod
    def describir(self) -> str: pass


class Cliente(Entidad):
    _VAL   = ValidadorCliente()
    _lista: list = []

    def __init__(self, id: int, nombre: str, documento: str, correo: str):
        super().__init__(id)
        err = self._VAL.validar({"nombre": nombre, "documento": documento, "correo": correo})
        if err:
            raise DatoInvalidoError("datos_cliente", " | ".join(err))
        self.__nombre    = str(nombre).strip()
        self.__documento = str(documento).strip()
        self.__correo    = str(correo).strip().lower()
        Cliente._lista.append(self)
        Logger.info(f"Cliente: #{id} {self.__nombre}")

    def get_nombre(self)    -> str: return self.__nombre
    def get_documento(self) -> str: return self.__documento
    def get_correo(self)    -> str: return self.__correo

    def describir(self) -> str:
        return f"Cliente #{self._id} | {self.__nombre} | {self.__documento} | {self.__correo}"

    @classmethod
    def total(cls) -> int: return len(cls._lista)

    @classmethod
    def reset(cls): cls._lista.clear()


class Servicio(Entidad, ABC):
    _VAL = ValidadorServicio()

    def __init__(self, id: int, nombre: str, precio_base: float, disponible: bool = True):
        super().__init__(id)
        err = self._VAL.validar({"nombre": nombre, "precio_base": precio_base, "tipo": type(self).__name__})
        if err:
            raise DatoInvalidoError("datos_servicio", " | ".join(err))
        self.__nombre      = str(nombre).strip()
        self.__precio_base = float(precio_base)
        self.__disponible  = disponible

    def get_nombre(self)      -> str:   return self.__nombre
    def get_precio_base(self) -> float: return self.__precio_base
    def esta_disponible(self) -> bool:  return self.__disponible
    def set_disponibilidad(self, v: bool): self.__disponible = v

    @abstractmethod
    def calcular_costo(self, duracion: int) -> float: pass

    @abstractmethod
    def describir(self) -> str: pass


class ReservaSala(Servicio):
    def calcular_costo(self, d: int) -> float: return self.get_precio_base() * d * 1.10
    def describir(self) -> str:
        return f"[Sala]   {self.get_nombre()} ${self.get_precio_base():,.0f}/hr (+10%)"


class AlquilerEquipo(Servicio):
    def calcular_costo(self, d: int) -> float: return self.get_precio_base() * d * 0.95
    def describir(self) -> str:
        return f"[Equipo] {self.get_nombre()} ${self.get_precio_base():,.0f}/hr (-5%)"


class Asesoria(Servicio):
    def calcular_costo(self, d: int) -> float: return self.get_precio_base() * d * 1.50
    def describir(self) -> str:
        return f"[Asesor] {self.get_nombre()} ${self.get_precio_base():,.0f}/hr (+50%)"


class Reserva(Entidad):
    _VAL_R  = ValidadorReserva()
    _VAL_K  = ValidadorCalculo()
    _lista: list = []

    TRANS = {
        "pendiente":  {"confirmar", "cancelar"},
        "confirmada": {"cancelar",  "finalizar"},
        "cancelada":  set(),
        "finalizada": set(),
    }

    def __init__(self, id: int, cliente: Cliente, servicio: Servicio, duracion: int):
        super().__init__(id)
        err = self._VAL_R.validar({
            "cliente_id": cliente.get_id() if isinstance(cliente, Cliente) else None,
            "servicio_id": servicio.get_id() if isinstance(servicio, Servicio) else None,
            "duracion":    duracion,
            "servicio_disponible": servicio.esta_disponible() if isinstance(servicio, Servicio) else False,
        })
        if err:
            raise ReservaInvalidaError(" | ".join(err))
        self.__cliente  = cliente
        self.__servicio = servicio
        self.__duracion = duracion
        self.__estado   = "pendiente"
        self.__fecha    = datetime.now()
        self.__codigo   = f"RES-{id:04d}-{self.__fecha.strftime('%Y%m%d%H%M%S')}"
        Reserva._lista.append(self)
        Logger.info(f"Reserva: {self.__codigo}")

    def _check(self, op: str):
        if op not in self.TRANS.get(self.__estado, set()):
            raise OperacionNoPermitidaError(op, self.__estado)

    def confirmar(self) -> bool:
        try:
            self._check("confirmar")
            costo = self.__servicio.calcular_costo(self.__duracion)
            self.__estado = "confirmada"
            Logger.info(f"Confirmada: {self.__codigo} ${costo:,.0f}")
            return True
        except (OperacionNoPermitidaError, CalculoInconsistenteError):
            raise
        finally:
            Logger.info(f"[finally] confirmar() estado={self.__estado}")

    def cancelar(self, motivo: str = "—") -> bool:
        try:
            self._check("cancelar")
            self.__estado = "cancelada"
            self.__servicio.set_disponibilidad(True)
            Logger.info(f"Cancelada: {self.__codigo} | {motivo}")
            return True
        except OperacionNoPermitidaError:
            raise
        finally:
            Logger.info(f"[finally] cancelar() estado={self.__estado}")

    def finalizar(self) -> bool:
        self._check("finalizar")
        self.__estado = "finalizada"
        self.__servicio.set_disponibilidad(True)
        Logger.info(f"Finalizada: {self.__codigo}")
        return True

    def calcular_total(self, tasa: float = 0.0, descuento: float = 0.0) -> float:
        base = self.__servicio.calcular_costo(self.__duracion)
        err  = self._VAL_K.validar({"tasa_impuesto": tasa, "descuento": descuento, "costo_base": base})
        if err:
            raise CalculoInconsistenteError(" | ".join(err))
        return max(0.0, base * (1 + tasa) - descuento)

    def describir(self) -> str:
        return (f"Reserva {self.__codigo} | {self.__cliente.get_nombre()} | "
                f"{self.__servicio.get_nombre()} | {self.__duracion}h | {self.__estado.upper()}")

    def get_codigo(self) -> str: return self.__codigo
    def get_estado(self) -> str: return self.__estado

    @classmethod
    def total(cls) -> int: return len(cls._lista)

    @classmethod
    def reset(cls): cls._lista.clear()


# ═══════════════════════════════════════════════════════════
# LAS 10 OPERACIONES (capturan su salida como texto)
# ═══════════════════════════════════════════════════════════

def _capturar(fn) -> str:
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        fn()
    finally:
        sys.stdout = old
    return buf.getvalue()


def _sep(num: int, titulo: str, buf: list):
    buf.append(("title", f"\n{'═'*54}\n  OPERACIÓN {num:02d}: {titulo}\n{'═'*54}"))


def op01(buf: list):
    _sep(1, "REGISTRO DE CLIENTE VÁLIDO", buf)
    try:
        c = Cliente(1, "María López", "10987654", "maria@correo.com")
        buf.append(("ok", f"  OK   {c.describir()}"))
    except DatoInvalidoError as e:
        buf.append(("error", f"  ERROR  {e}"))
    else:
        buf.append(("info", "       Bloque else ejecutado — sin errores"))
    finally:
        buf.append(("dim", "       [finally] siempre se ejecuta"))


def op02(buf: list):
    _sep(2, "REGISTRO DE CLIENTES INVÁLIDOS", buf)
    casos = [
        (2, "",        "12345678", "ok@mail.com",   "Nombre vacío"),
        (3, "AB",      "12345678", "ok@mail.com",   "Nombre < 3 chars"),
        (4, "Pedro",   "123",      "ok@mail.com",   "Documento muy corto"),
        (5, "Ana Ruiz","1234567",  "sin-arroba",    "Correo sin @"),
        (6, "Tomas V", "ABCD123",  "ok@mail.com",   "Documento no numérico"),
    ]
    for id_, n, d, c, desc in casos:
        try:
            Cliente(id_, n, d, c)
            buf.append(("warn", f"  AVISO  [{desc}] — debía rechazarse"))
        except DatoInvalidoError as e:
            buf.append(("error", f"  CAPT.  [{desc}] → {e}"))
        finally:
            buf.append(("dim", f"         [finally] caso '{desc}' cerrado"))


def op03(buf: list):
    _sep(3, "CREACIÓN DE SERVICIOS VÁLIDOS", buf)
    creados = []
    try:
        s1 = ReservaSala(1,    "Sala Principal",       50_000, True)
        s2 = AlquilerEquipo(2, "Proyector 4K",         20_000, True)
        s3 = Asesoria(3,       "Consultoría Jurídica", 150_000, True)
        creados = [s1, s2, s3]
        for s in creados:
            buf.append(("ok", f"  OK   {s.describir()}"))
    except DatoInvalidoError as e:
        buf.append(("error", f"  ERROR  {e}"))
    else:
        buf.append(("info", f"       {len(creados)} servicios creados (bloque else)"))


def op04(buf: list):
    _sep(4, "CREACIÓN DE SERVICIOS INVÁLIDOS", buf)
    casos = [
        ("Nombre vacío",    lambda: ReservaSala(10,    "",       50_000, True)),
        ("Precio negativo", lambda: AlquilerEquipo(11, "Laptop", -5_000, True)),
        ("Precio cero",     lambda: Asesoria(12,       "Test",   0,      True)),
        ("Precio excesivo", lambda: ReservaSala(13,    "Sala B", 99_000_000, True)),
    ]
    for desc, ctor in casos:
        try:
            s = ctor()
            buf.append(("warn", f"  AVISO  [{desc}] — debía rechazarse"))
        except DatoInvalidoError as e:
            buf.append(("error", f"  CAPT.  [{desc}] → {e}"))


def op05(buf: list) -> object:
    _sep(5, "RESERVA EXITOSA", buf)
    reserva = None
    try:
        c       = Cliente(50, "Diego Vargas",   "3344556", "diego@main.com")
        s       = ReservaSala(50, "Sala Ejecutiva", 60_000, True)
        reserva = Reserva(1, c, s, 3)
        buf.append(("ok", f"  OK   Creada: {reserva.describir()}"))
        reserva.confirmar()
        buf.append(("ok", f"  OK   Confirmada | Código: {reserva.get_codigo()}"))
        t0 = reserva.calcular_total()
        t1 = reserva.calcular_total(0.19)
        t2 = reserva.calcular_total(0.19, 20_000)
        buf.append(("info", f"       Base:              ${t0:>12,.0f}"))
        buf.append(("info", f"       + 19% IVA:         ${t1:>12,.0f}"))
        buf.append(("info", f"       + IVA - $20k desc: ${t2:>12,.0f}"))
    except ErrorSistema as e:
        buf.append(("error", f"  ERROR  {e}"))
    finally:
        buf.append(("dim", "       [finally] OP05 finalizada"))
    return reserva


def op06(buf: list):
    _sep(6, "RESERVA FALLIDA — SERVICIO NO DISPONIBLE", buf)
    try:
        s = ReservaSala(60, "Sala VIP",   80_000, False)
        c = Cliente(61,     "Juan Media", "10998877", "juan@test.com")
        r = Reserva(2, c, s, 2)
        buf.append(("warn", f"  AVISO  debía rechazarse: {r.describir()}"))
    except ServicioNoDisponibleError as e:
        buf.append(("error", f"  CAPT.  ServicioNoDisponibleError → {e}"))
    except ErrorSistema as e:
        buf.append(("error", f"  CAPT.  ErrorSistema → {e}"))
    else:
        buf.append(("warn", "       (bloque else: no se esperaba llegar aquí)"))
    finally:
        buf.append(("dim", "       [finally] OP06 cerrada"))


def op07(buf: list, reserva):
    _sep(7, "CANCELACIÓN DE RESERVA + ENCADENAMIENTO", buf)
    if reserva is None:
        buf.append(("warn", "  AVISO  Reserva no disponible (OP05 falló)"))
        return

    # Cancelación válida (desde estado "confirmada")
    try:
        reserva.cancelar("Cambio de agenda")
        buf.append(("ok", f"  OK   Cancelada: {reserva.describir()}"))
    except OperacionNoPermitidaError as e:
        buf.append(("error", f"  ERROR  {e}"))

    # Segundo intento → encadenamiento
    buf.append(("info", "\n  Segundo intento de cancelación (debe fallar):"))
    try:
        try:
            reserva.cancelar("Reintento")
        except OperacionNoPermitidaError as causa:
            raise ReservaInvalidaError("Cancelación duplicada") from causa
    except ReservaInvalidaError as final:
        buf.append(("error", f"  ENCAD  ReservaInvalidaError: {final}"))
        buf.append(("dim",   f"         └─ causa: {type(final.__cause__).__name__}: {final.__cause__}"))


def op08(buf: list):
    _sep(8, "CÁLCULO SOBRECARGADO CON IMPUESTOS Y DESCUENTOS", buf)
    try:
        c = Cliente(80, "Ana Morales", "1111222", "ana@test.com")
        s = Asesoria(80, "Asesoría Contable", 120_000, True)
        r = Reserva(3, c, s, 2)

        t0 = r.calcular_total()
        t1 = r.calcular_total(0.19)
        t2 = r.calcular_total(0.19, 20_000)
        t3 = r.calcular_total(0.0,  10_000)
        buf.append(("ok",  f"  OK   Costo base:                    ${t0:>12,.0f}"))
        buf.append(("ok",  f"       + 19% IVA:                     ${t1:>12,.0f}"))
        buf.append(("ok",  f"       + 19% IVA  - $20.000 desc.:    ${t2:>12,.0f}"))
        buf.append(("ok",  f"       Sin imp.   - $10.000 desc.:     ${t3:>12,.0f}"))

        # Intento de cálculo inválido
        buf.append(("info", "\n  Intento con tasa > 1 (debe rechazarse):"))
        r.calcular_total(2.5)
    except CalculoInconsistenteError as e:
        buf.append(("error", f"  CAPT.  CalculoInconsistenteError → {e}"))


def op09(buf: list):
    _sep(9, "PATRONES try/except/else/finally + ENCADENAMIENTO", buf)
    buf.append(("info", "  Patrón try / except / else / finally:"))
    try:
        c = Cliente(90, "Luis Torres", "5566778", "luis@test.com")
        s = AlquilerEquipo(90, "Drone DJI", 45_000, True)
        r = Reserva(4, c, s, 5)
        r.confirmar()
    except DatoInvalidoError as e:
        buf.append(("error", f"    except DatoInvalidoError: {e}"))
    except ServicioNoDisponibleError as e:
        buf.append(("error", f"    except ServicioNoDisponibleError: {e}"))
    except ErrorSistema as e:
        buf.append(("error", f"    except ErrorSistema: {e}"))
    else:
        buf.append(("ok", f"    else (sin errores): {r.describir()}"))
    finally:
        buf.append(("dim", "    finally: siempre se ejecuta"))

    buf.append(("info", "\n  Encadenamiento de excepciones:"))
    try:
        try:
            raise DatoInvalidoError("campo_prueba", "valor_invalido")
        except DatoInvalidoError as original:
            raise OperacionNoPermitidaError("procesar", "error") from original
    except OperacionNoPermitidaError as final:
        buf.append(("error", f"    Excepción final  : {type(final).__name__}: {final}"))
        buf.append(("dim",   f"    Causa encadenada : {type(final.__cause__).__name__}: {final.__cause__}"))

    buf.append(("info", "\n  Re-lanzamiento desde bloque except:"))
    try:
        try:
            Cliente(99, "", "12345678", "ok@ok.com")
        except DatoInvalidoError:
            raise ErrorSistema("Datos rechazados — re-lanzamiento enriquecido", "E010")
    except ErrorSistema as e:
        buf.append(("error", f"    Re-lanzado [{e.codigo}]: {e}"))


def op10(buf: list):
    _sep(10, "LOTE MIXTO — RECUPERACIÓN ANTE ERRORES CRÍTICOS", buf)
    buf.append(("info", "  El sistema procesa el lote completo sin detenerse.\n"))
    lote = [
        (200, "Sandra Ríos",   "9988776", "sandra@correo.com"),
        (201, "X",             "123",     "mailroto"),
        (202, "Andrés Paz",    "1122334", "andres@correo.com"),
        (203, "",              "9876543", "empty@test.com"),
        (204, "Laura Cano",    "7654321", "laura@valid.com"),
        (205, "Tomas Vera",    "4433221", "tomas@test.co"),
        (206, "Carmen Gil",    "3344556", "carmen@gil.co"),
        (207, "M",             "12345",   "m@m.com"),
    ]
    ok = 0
    for id_c, nombre, doc, correo in lote:
        try:
            c = Cliente(id_c, nombre, doc, correo)
            buf.append(("ok",    f"  OK   [{id_c}] {c.get_nombre()}"))
            ok += 1
        except DatoInvalidoError as e:
            buf.append(("error", f"  FALLO [{id_c}] {e}"))
        except ErrorSistema as e:
            buf.append(("error", f"  CRIT  [{id_c}] [{e.codigo}] {e}"))
        finally:
            pass

    buf.append(("info",  f"\n  Resumen del lote:"))
    buf.append(("ok",    f"    Procesados : {len(lote)}"))
    buf.append(("ok",    f"    Exitosos   : {ok}"))
    buf.append(("error", f"    Fallidos   : {len(lote) - ok}"))
    buf.append(("info",  f"\n  Estado global:"))
    buf.append(("info",  f"    Clientes registrados : {Cliente.total()}"))
    buf.append(("info",  f"    Reservas en sistema  : {Reserva.total()}"))


OPERACIONES = [
    ("OP01 — Registro cliente válido",           op01),
    ("OP02 — Clientes inválidos",                op02),
    ("OP03 — Servicios válidos",                 op03),
    ("OP04 — Servicios inválidos",               op04),
    ("OP05 — Reserva exitosa",                   op05),
    ("OP06 — Reserva fallida",                   op06),
    ("OP07 — Cancelación + encadenamiento",      None),
    ("OP08 — Cálculo sobrecargado",              op08),
    ("OP09 — try/except/else/finally",           op09),
    ("OP10 — Lote mixto + recuperación",         op10),
]


# ═══════════════════════════════════════════════════════════
# INTERFAZ GRÁFICA
# ═══════════════════════════════════════════════════════════

PALETA = {
    "bg":        "#1e1e2e",
    "sidebar":   "#181825",
    "card":      "#2a2a3e",
    "panel":     "#11111b",
    "border":    "#313244",
    "ok":        "#a6e3a1",
    "error":     "#f38ba8",
    "warn":      "#f9e2af",
    "info":      "#89b4fa",
    "title":     "#cba6f7",
    "dim":       "#6c7086",
    "text":      "#cdd6f4",
    "accent":    "#cba6f7",
    "btn_bg":    "#313244",
    "btn_hover": "#45475a",
    "btn_run":   "#89dceb",
    "btn_all":   "#a6e3a1",
    "header_fg": "#cdd6f4",
}

TAG_COLOR = {
    "ok":    PALETA["ok"],
    "error": PALETA["error"],
    "warn":  PALETA["warn"],
    "info":  PALETA["info"],
    "title": PALETA["title"],
    "dim":   PALETA["dim"],
}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sistema de Gestión — Clientes, Servicios y Reservas")
        self.geometry("1180x720")
        self.minsize(900, 580)
        self.configure(bg=PALETA["bg"])
        self._reserva_op05 = None
        self._build_ui()

    # ── Construcción de la UI ───────────────────────────────
    def _build_ui(self):
        self._build_header()
        body = tk.Frame(self, bg=PALETA["bg"])
        body.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)
        self._build_sidebar(body)
        self._build_main(body)

    def _build_header(self):
        hdr = tk.Frame(self, bg=PALETA["sidebar"], height=52)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        tk.Label(
            hdr,
            text="⚙  Sistema de Gestión — Clientes · Servicios · Reservas",
            fg=PALETA["header_fg"],
            bg=PALETA["sidebar"],
            font=("Segoe UI", 13, "bold"),
            anchor="w",
        ).pack(side="left", padx=18, pady=12)

        self._lbl_status = tk.Label(
            hdr,
            text="Listo",
            fg=PALETA["dim"],
            bg=PALETA["sidebar"],
            font=("Segoe UI", 10),
        )
        self._lbl_status.pack(side="right", padx=18)

    def _build_sidebar(self, parent):
        side = tk.Frame(parent, bg=PALETA["sidebar"], width=240)
        side.grid(row=0, column=0, sticky="nsw", padx=(0, 10), pady=6)
        side.grid_propagate(False)

        tk.Label(
            side,
            text="OPERACIONES",
            fg=PALETA["dim"],
            bg=PALETA["sidebar"],
            font=("Segoe UI", 8, "bold"),
            anchor="w",
        ).pack(fill="x", padx=12, pady=(14, 6))

        self._op_btns = []
        for i, (nombre, _) in enumerate(OPERACIONES):
            btn = tk.Button(
                side,
                text=nombre,
                bg=PALETA["btn_bg"],
                fg=PALETA["text"],
                activebackground=PALETA["btn_hover"],
                activeforeground=PALETA["text"],
                relief="flat",
                anchor="w",
                padx=12,
                pady=7,
                font=("Segoe UI", 9),
                cursor="hand2",
                command=lambda idx=i: self._run_op(idx),
            )
            btn.pack(fill="x", padx=8, pady=2)
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=PALETA["btn_hover"]))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=PALETA["btn_bg"]))
            self._op_btns.append(btn)

        sep = tk.Frame(side, bg=PALETA["border"], height=1)
        sep.pack(fill="x", padx=8, pady=10)

        btn_all = tk.Button(
            side,
            text="▶  Ejecutar TODAS las operaciones",
            bg=PALETA["btn_all"],
            fg=PALETA["bg"],
            activebackground="#94d68f",
            activeforeground=PALETA["bg"],
            relief="flat",
            padx=12,
            pady=9,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
            command=self._run_all,
        )
        btn_all.pack(fill="x", padx=8, pady=2)

        btn_clear = tk.Button(
            side,
            text="⌫  Limpiar pantalla",
            bg=PALETA["btn_bg"],
            fg=PALETA["dim"],
            activebackground=PALETA["btn_hover"],
            activeforeground=PALETA["text"],
            relief="flat",
            padx=12,
            pady=7,
            font=("Segoe UI", 9),
            cursor="hand2",
            command=self._clear,
        )
        btn_clear.pack(fill="x", padx=8, pady=2)

        btn_log = tk.Button(
            side,
            text="📄  Ver archivo de log",
            bg=PALETA["btn_bg"],
            fg=PALETA["dim"],
            activebackground=PALETA["btn_hover"],
            activeforeground=PALETA["text"],
            relief="flat",
            padx=12,
            pady=7,
            font=("Segoe UI", 9),
            cursor="hand2",
            command=self._show_log,
        )
        btn_log.pack(fill="x", padx=8, pady=2)

    def _build_main(self, parent):
        main = tk.Frame(parent, bg=PALETA["bg"])
        main.grid(row=0, column=1, sticky="nsew", pady=6)
        main.rowconfigure(0, weight=1)
        main.columnconfigure(0, weight=1)

        # Panel de salida
        out_frame = tk.Frame(main, bg=PALETA["panel"], bd=0, relief="flat",
                             highlightbackground=PALETA["border"], highlightthickness=1)
        out_frame.grid(row=0, column=0, sticky="nsew")
        out_frame.rowconfigure(1, weight=1)
        out_frame.columnconfigure(0, weight=1)

        bar = tk.Frame(out_frame, bg=PALETA["card"], height=30)
        bar.grid(row=0, column=0, sticky="ew")
        tk.Label(
            bar,
            text="  SALIDA",
            fg=PALETA["dim"],
            bg=PALETA["card"],
            font=("Segoe UI", 8, "bold"),
            anchor="w",
        ).pack(side="left", padx=6, pady=5)

        self._out = scrolledtext.ScrolledText(
            out_frame,
            bg=PALETA["panel"],
            fg=PALETA["text"],
            insertbackground=PALETA["text"],
            selectbackground=PALETA["border"],
            font=("Consolas", 10),
            relief="flat",
            wrap="word",
            state="disabled",
            padx=14,
            pady=10,
        )
        self._out.grid(row=1, column=0, sticky="nsew")

        # Configurar colores de tags
        for tag, color in TAG_COLOR.items():
            self._out.tag_configure(tag, foreground=color)
        self._out.tag_configure("title", foreground=PALETA["title"],
                                font=("Consolas", 10, "bold"))
        self._out.tag_configure("dim", foreground=PALETA["dim"])

        self._write_welcome()

    # ── Escritura en el panel ───────────────────────────────
    def _write(self, texto: str, tag: str = ""):
        self._out.config(state="normal")
        if tag:
            self._out.insert("end", texto + "\n", tag)
        else:
            self._out.insert("end", texto + "\n")
        self._out.see("end")
        self._out.config(state="disabled")

    def _write_buf(self, buf: list):
        self._out.config(state="normal")
        for tag, texto in buf:
            if tag in TAG_COLOR or tag in ("title", "dim"):
                self._out.insert("end", texto + "\n", tag)
            else:
                self._out.insert("end", texto + "\n")
        self._out.see("end")
        self._out.config(state="disabled")

    def _write_welcome(self):
        lineas = [
            ("title", "╔══════════════════════════════════════════════════════╗"),
            ("title", "║   Sistema de Gestión de Clientes y Reservas          ║"),
            ("title", "║   Operaciones 01-10 · Excepciones · Validaciones     ║"),
            ("title", "╚══════════════════════════════════════════════════════╝"),
            ("dim",   ""),
            ("info",  "  Selecciona una operación en el panel izquierdo,"),
            ("info",  "  o pulsa 'Ejecutar TODAS las operaciones'."),
            ("dim",   ""),
        ]
        self._write_buf(lineas)

    # ── Lógica de ejecución ─────────────────────────────────
    def _reset_state(self):
        Cliente.reset()
        Reserva.reset()
        self._reserva_op05 = None

    def _run_op(self, idx: int):
        self._set_status(f"Ejecutando {OPERACIONES[idx][0]}…")
        nombre, fn = OPERACIONES[idx]
        buf = []

        if idx == 6:
            op07(buf, self._reserva_op05)
        elif idx == 4:
            self._reset_state()
            r = op05(buf)
            self._reserva_op05 = r
        else:
            if fn is not None:
                fn(buf)

        self._write_buf(buf)
        self._set_status(f"Completado: {nombre}")
        self._highlight_btn(idx)

    def _run_all(self):
        self._clear()
        self._reset_state()
        self._set_status("Ejecutando todas las operaciones…")
        buf = []

        op01(buf)
        op02(buf)
        op03(buf)
        op04(buf)

        # OP05 guarda la reserva para OP07
        r05_buf = []
        r = op05(r05_buf)
        buf.extend(r05_buf)
        self._reserva_op05 = r

        op06(buf)
        op07(buf, r)
        op08(buf)
        op09(buf)
        op10(buf)

        buf.append(("dim",   ""))
        buf.append(("title", f"{'═'*54}"))
        buf.append(("title", f"  TODAS LAS OPERACIONES COMPLETADAS"))
        buf.append(("info",  f"  Clientes: {Cliente.total()} | Reservas: {Reserva.total()}"))
        buf.append(("title", f"{'═'*54}"))

        self._write_buf(buf)
        self._set_status("Todas las operaciones completadas.")
        Logger.info(f"Sesión completa — Clientes={Cliente.total()} Reservas={Reserva.total()}")

    def _clear(self):
        self._out.config(state="normal")
        self._out.delete("1.0", "end")
        self._out.config(state="disabled")
        self._write_welcome()
        self._set_status("Pantalla limpiada")
        for btn in self._op_btns:
            btn.config(bg=PALETA["btn_bg"])

    def _show_log(self):
        win = tk.Toplevel(self)
        win.title("Archivo de Log — " + LOG_FILE)
        win.geometry("900x520")
        win.configure(bg=PALETA["bg"])

        bar = tk.Frame(win, bg=PALETA["card"])
        bar.pack(fill="x")
        tk.Label(bar, text=f"  {LOG_FILE}", fg=PALETA["dim"],
                 bg=PALETA["card"], font=("Segoe UI", 9, "bold")).pack(
            side="left", padx=8, pady=6)
        tk.Button(bar, text="↺ Refrescar", bg=PALETA["btn_bg"],
                  fg=PALETA["text"], relief="flat", padx=8,
                  command=lambda: _reload()).pack(side="right", padx=8, pady=4)

        txt = scrolledtext.ScrolledText(
            win,
            bg=PALETA["panel"],
            fg=PALETA["text"],
            font=("Consolas", 9),
            relief="flat",
            padx=10,
            pady=8,
        )
        txt.pack(fill="both", expand=True)
        txt.tag_configure("err",  foreground=PALETA["error"])
        txt.tag_configure("warn", foreground=PALETA["warn"])
        txt.tag_configure("info", foreground=PALETA["info"])
        txt.tag_configure("crit", foreground="#ff5555")

        def _reload():
            txt.delete("1.0", "end")
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, encoding="utf-8") as f:
                    for linea in f:
                        if "[ERROR" in linea or "[CRITICO" in linea:
                            txt.insert("end", linea, "err")
                        elif "[WARNING" in linea:
                            txt.insert("end", linea, "warn")
                        else:
                            txt.insert("end", linea, "info")
            else:
                txt.insert("end", f"  (archivo '{LOG_FILE}' no existe todavía)\n")
            txt.see("end")

        _reload()

    def _set_status(self, msg: str):
        self._lbl_status.config(text=msg)
        self.update_idletasks()

    def _highlight_btn(self, idx: int):
        for i, btn in enumerate(self._op_btns):
            btn.config(bg=PALETA["btn_bg"])
        self._op_btns[idx].config(bg=PALETA["btn_hover"])


# ─── Punto de entrada ─────────────────────────────────────────
if __name__ == "__main__":
    Logger.info("=" * 40 + " INTERFAZ INICIADA " + "=" * 40)
    app = App()
    app.mainloop()
    Logger.info("=" * 40 + " INTERFAZ CERRADA " + "=" * 40)
