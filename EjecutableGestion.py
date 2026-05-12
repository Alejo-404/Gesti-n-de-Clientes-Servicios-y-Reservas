# ============================================================
# OPERACIÓN 09 - MANEJO DE EXCEPCIONES Y LOGS
# Sistema de Gestión de Clientes, Servicios y Reservas
# ============================================================
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from abc import ABC, abstractmethod
from datetime import datetime
import os


# ─── Logger ──────────────────────────────────────────────────
class Logger:
    ARCHIVO = "sistema_gestion.log"

    @staticmethod
    def registrar(nivel: str, mensaje: str):
        try:
            ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            linea = f"[{nivel.upper():<8}] {ts} | {mensaje}\n"
            with open(Logger.ARCHIVO, "a", encoding="utf-8") as f:
                f.write(linea)
        except OSError as e:
            print(f"  [LOG-ERR] No se pudo escribir en archivo: {e}")

    @classmethod
    def info(cls, msg):    cls.registrar("INFO",    msg)
    @classmethod
    def error(cls, msg):   cls.registrar("ERROR",   msg)
    @classmethod
    def warn(cls, msg):    cls.registrar("WARNING", msg)
    @classmethod
    def critico(cls, msg): cls.registrar("CRITICO", msg)


# ─── Jerarquía de Excepciones Personalizadas ─────────────────
class ErrorSistema(Exception):
    def __init__(self, mensaje: str, codigo: str = "E000"):
        super().__init__(mensaje)
        self.codigo = codigo
        Logger.error(f"[{codigo}] {mensaje}")


class DatoInvalidoError(ErrorSistema):
    def __init__(self, campo: str, valor=None):
        detalle = f": '{valor}'" if valor is not None else ""
        super().__init__(f"Dato inválido en '{campo}'{detalle}", "E001")
        self.campo = campo


class ParametroFaltanteError(ErrorSistema):
    def __init__(self, parametro: str):
        super().__init__(f"Parámetro requerido faltante: '{parametro}'", "E002")
        self.parametro = parametro


class ServicioNoDisponibleError(ErrorSistema):
    def __init__(self, nombre: str):
        super().__init__(f"Servicio no disponible: '{nombre}'", "E003")


class ReservaInvalidaError(ErrorSistema):
    def __init__(self, motivo: str):
        super().__init__(f"Reserva inválida: {motivo}", "E004")


class OperacionNoPermitidaError(ErrorSistema):
    def __init__(self, operacion: str, estado_actual: str):
        super().__init__(
            f"Operación '{operacion}' no permitida. Estado actual: '{estado_actual}'", "E005"
        )


class CalculoInconsistenteError(ErrorSistema):
    def __init__(self, detalle: str):
        super().__init__(f"Cálculo inconsistente: {detalle}", "E006")


# ─── Clase Base Abstracta ────────────────────────────────────
class Entidad(ABC):
    def __init__(self, id: int):
        if not isinstance(id, int) or id <= 0:
            raise DatoInvalidoError("id", id)
        self._id = id

    def get_id(self) -> int:
        return self._id

    @abstractmethod
    def describir(self) -> str:
        pass


# ─── Cliente ─────────────────────────────────────────────────
class Cliente(Entidad):
    _registro: list = []

    def __init__(self, id: int, nombre: str, documento: str, correo: str, telefono: str = ""):
        super().__init__(id)
        self._validar(nombre, documento, correo)
        self.__nombre    = nombre.strip()
        self.__documento = documento.strip()
        self.__correo    = correo.strip().lower()
        self.__telefono  = telefono.strip()
        Cliente._registro.append(self)
        Logger.info(f"Cliente registrado: #{id} {self.__nombre} ({self.__documento})")

    def _validar(self, nombre: str, documento: str, correo: str):
        if not nombre or not nombre.strip():
            raise DatoInvalidoError("nombre")
        if len(nombre.strip()) < 3:
            raise DatoInvalidoError("nombre (mínimo 3 caracteres)", nombre)
        if not documento or not documento.strip().isdigit() or len(documento.strip()) < 7:
            raise DatoInvalidoError("documento (mínimo 7 dígitos numéricos)", documento)
        if not correo or "@" not in correo or "." not in correo.split("@")[-1]:
            raise DatoInvalidoError("correo", correo)

    def get_nombre(self)    -> str: return self.__nombre
    def get_documento(self) -> str: return self.__documento
    def get_correo(self)    -> str: return self.__correo

    def describir(self) -> str:
        return (f"Cliente #{self._id} | {self.__nombre} | "
                f"Doc: {self.__documento} | {self.__correo}")

    @classmethod
    def total(cls) -> int:
        return len(cls._registro)


# ─── Servicio (Abstracto) + 3 Especializaciones ──────────────
class Servicio(Entidad, ABC):
    def __init__(self, id: int, nombre: str, precio_base: float, disponible: bool = True):
        super().__init__(id)
        if not nombre or not nombre.strip():
            raise DatoInvalidoError("nombre del servicio")
        if not isinstance(precio_base, (int, float)) or precio_base <= 0:
            raise DatoInvalidoError("precio_base (debe ser positivo)", precio_base)
        self.__nombre      = nombre.strip()
        self.__precio_base = float(precio_base)
        self.__disponible  = disponible

    def get_nombre(self)       -> str:   return self.__nombre
    def get_precio_base(self)  -> float: return self.__precio_base
    def esta_disponible(self)  -> bool:  return self.__disponible
    def set_disponibilidad(self, estado: bool): self.__disponible = estado

    @abstractmethod
    def calcular_costo(self, duracion: int) -> float:
        pass

    @abstractmethod
    def describir(self) -> str:
        pass


class ReservaSala(Servicio):
    FACTOR = 1.10

    def calcular_costo(self, duracion: int) -> float:
        if duracion <= 0:
            raise CalculoInconsistenteError(f"Duración inválida: {duracion}")
        return self.get_precio_base() * duracion * self.FACTOR

    def describir(self) -> str:
        return f"[Sala]    {self.get_nombre()} | ${self.get_precio_base():>10,.0f}/hr (+10%)"


class AlquilerEquipo(Servicio):
    FACTOR = 0.95

    def calcular_costo(self, duracion: int) -> float:
        if duracion <= 0:
            raise CalculoInconsistenteError(f"Duración inválida: {duracion}")
        return self.get_precio_base() * duracion * self.FACTOR

    def describir(self) -> str:
        return f"[Equipo]  {self.get_nombre()} | ${self.get_precio_base():>10,.0f}/hr (-5%)"


class Asesoria(Servicio):
    FACTOR = 1.50

    def calcular_costo(self, duracion: int) -> float:
        if duracion <= 0:
            raise CalculoInconsistenteError(f"Duración inválida: {duracion}")
        return self.get_precio_base() * duracion * self.FACTOR

    def describir(self) -> str:
        return f"[Asesoría]{self.get_nombre()} | ${self.get_precio_base():>10,.0f}/hr (+50%)"


# ─── Reserva ─────────────────────────────────────────────────
class Reserva(Entidad):
    _historial: list = []

    def __init__(self, id: int, cliente: Cliente, servicio: Servicio, duracion: int):
        super().__init__(id)
        try:
            self._validar_creacion(cliente, servicio, duracion)
            self.__cliente  = cliente
            self.__servicio = servicio
            self.__duracion = duracion
            self.__estado   = "pendiente"
            self.__fecha    = datetime.now()
            self.__codigo   = f"RES-{id:04d}-{self.__fecha.strftime('%Y%m%d%H%M%S')}"
            Reserva._historial.append(self)
            Logger.info(
                f"Reserva creada: {self.__codigo} | "
                f"{cliente.get_nombre()} | {servicio.get_nombre()} | {duracion}h"
            )
        except ErrorSistema:
            raise
        except Exception as e:
            raise ErrorSistema(f"Error inesperado al crear reserva: {e}", "E099") from e

    def _validar_creacion(self, cliente, servicio, duracion):
        if not isinstance(cliente, Cliente):
            raise DatoInvalidoError("cliente")
        if not isinstance(servicio, Servicio):
            raise DatoInvalidoError("servicio")
        if not isinstance(duracion, int) or duracion <= 0:
            raise ParametroFaltanteError("duracion (entero positivo)")
        if duracion > 24:
            raise DatoInvalidoError("duracion (máximo 24h)", duracion)
        if not servicio.esta_disponible():
            raise ServicioNoDisponibleError(servicio.get_nombre())

    def confirmar(self) -> bool:
        try:
            if self.__estado != "pendiente":
                raise OperacionNoPermitidaError("confirmar", self.__estado)
            costo = self.__servicio.calcular_costo(self.__duracion)
            if costo < 0:
                raise CalculoInconsistenteError("costo base negativo")
            self.__estado = "confirmada"
            Logger.info(f"Reserva confirmada: {self.__codigo} | Total base: ${costo:,.0f}")
            return True
        except (OperacionNoPermitidaError, CalculoInconsistenteError):
            raise
        except Exception as e:
            raise ErrorSistema(f"Fallo en confirmación: {e}", "E007") from e
        finally:
            Logger.info(f"  [finally] confirmar() finalizado | Estado: {self.__estado}")

    def cancelar(self, motivo: str = "No especificado") -> bool:
        try:
            if self.__estado in {"cancelada", "finalizada"}:
                raise OperacionNoPermitidaError("cancelar", self.__estado)
            self.__estado = "cancelada"
            self.__servicio.set_disponibilidad(True)
            Logger.info(f"Reserva cancelada: {self.__codigo} | Motivo: {motivo}")
            return True
        except OperacionNoPermitidaError as e:
            Logger.warn(f"Cancelación rechazada: {self.__codigo} | {e}")
            raise
        finally:
            Logger.info(f"  [finally] cancelar() finalizado | Estado: {self.__estado}")

    # Método sobrecargado: acepta 0, 1 o 2 parámetros opcionales
    def calcular_total(self, tasa_impuesto: float = 0.0, descuento: float = 0.0) -> float:
        try:
            if not (0.0 <= tasa_impuesto <= 1.0):
                raise DatoInvalidoError("tasa_impuesto (debe estar entre 0 y 1)", tasa_impuesto)
            if descuento < 0:
                raise DatoInvalidoError("descuento (no puede ser negativo)", descuento)
            base    = self.__servicio.calcular_costo(self.__duracion)
            impuesto = base * tasa_impuesto
            return max(0.0, (base + impuesto) - descuento)
        except ErrorSistema:
            raise
        except Exception as e:
            raise CalculoInconsistenteError(f"Error inesperado: {e}") from e

    def calcular_desglose(self, tasa_impuesto: float = 0.0, descuento: float = 0.0) -> dict:
        base     = self.__servicio.calcular_costo(self.__duracion)
        impuesto = base * tasa_impuesto
        total    = max(0.0, (base + impuesto) - descuento)
        return {
            "servicio":  self.__servicio.get_nombre(),
            "duracion":  self.__duracion,
            "base":      base,
            "impuesto":  impuesto,
            "descuento": descuento,
            "total":     total,
        }

    def describir(self) -> str:
        return (f"Reserva {self.__codigo} | {self.__cliente.get_nombre()} | "
                f"{self.__servicio.get_nombre()} | {self.__duracion}h | "
                f"{self.__estado.upper()}")

    def get_codigo(self) -> str:   return self.__codigo
    def get_estado(self) -> str:   return self.__estado

    @classmethod
    def total(cls) -> int:
        return len(cls._historial)


# ─── Utilidades de presentación ──────────────────────────────
def _sep(num: int, titulo: str):
    linea = "=" * 60
    print(f"\n{linea}")
    print(f"  OPERACIÓN {num:02d}: {titulo}")
    print(linea)
    Logger.info(f"{'─'*15} OPERACIÓN {num:02d}: {titulo} {'─'*15}")


# ─── Las 10 Operaciones ───────────────────────────────────────

def op01_registro_cliente_valido():
    _sep(1, "REGISTRO DE CLIENTE VÁLIDO")
    try:
        c = Cliente(1, "María López", "10987654", "maria@correo.com", "3001234567")
        print(f"  OK  {c.describir()}")
    except DatoInvalidoError as e:
        print(f"  ERROR  {e}")
    else:
        Logger.info("OP01 completada sin errores")


def op02_registro_cliente_invalido():
    _sep(2, "REGISTRO DE CLIENTES INVÁLIDOS")
    casos = [
        (2, "",          "12345678", "ok@mail.com",    "Nombre vacío"),
        (3, "AB",        "12345678", "ok@mail.com",    "Nombre < 3 chars"),
        (4, "Pedro Sol", "123",      "ok@mail.com",    "Documento muy corto"),
        (5, "Ana Ruiz",  "1234567",  "correo-roto",   "Correo sin @"),
        (6, "Test User", "ABC1234",  "ok@mail.com",    "Documento no numérico"),
    ]
    for id_, nombre, doc, correo, desc in casos:
        try:
            c = Cliente(id_, nombre, doc, correo)
            print(f"  INESPERADO  {c.describir()}")
        except DatoInvalidoError as e:
            print(f"  CAPTURADO  [{desc}] → {e}")
        finally:
            print(f"    [finally] caso '{desc}' procesado\n")


def op03_creacion_servicios_validos():
    _sep(3, "CREACIÓN DE SERVICIOS VÁLIDOS")
    servicios = []
    try:
        s1 = ReservaSala(1,    "Sala Principal",     50_000, True)
        s2 = AlquilerEquipo(2, "Proyector 4K",       20_000, True)
        s3 = Asesoria(3,       "Consultoría Jurídica", 150_000, True)
        servicios = [s1, s2, s3]
        for s in servicios:
            print(f"  OK  {s.describir()}")
    except DatoInvalidoError as e:
        print(f"  ERROR  {e}")
    else:
        Logger.info(f"OP03: {len(servicios)} servicios creados correctamente")
        print(f"\n  Total servicios creados: {len(servicios)}")
    return servicios


def op04_creacion_servicio_invalido():
    _sep(4, "CREACIÓN DE SERVICIOS INVÁLIDOS")
    casos = [
        ("Nombre vacío",       lambda: ReservaSala(10,    "",         50_000, True)),
        ("Precio negativo",    lambda: AlquilerEquipo(11, "Laptop",   -5_000, True)),
        ("Solo espacios",      lambda: Asesoria(12,       "   ",      80_000, True)),
        ("Precio cero",        lambda: ReservaSala(13,    "Sala B",   0,      True)),
    ]
    for desc, constructor in casos:
        try:
            s = constructor()
            print(f"  INESPERADO  {s.describir()}")
        except DatoInvalidoError as e:
            print(f"  CAPTURADO  [{desc}] → {e}")
        except Exception as e:
            Logger.critico(f"OP04 error inesperado [{desc}]: {type(e).__name__}: {e}")
            print(f"  CRITICO  {type(e).__name__}: {e}")


def op05_reserva_exitosa(cliente: Cliente, servicio: Servicio):
    _sep(5, "RESERVA EXITOSA")
    reserva = None
    try:
        reserva = Reserva(1, cliente, servicio, 3)
        print(f"  OK  Reserva creada: {reserva.describir()}")
        reserva.confirmar()
        print(f"  OK  Confirmada | Código: {reserva.get_codigo()}")
        d = reserva.calcular_desglose(tasa_impuesto=0.19)
        print(f"      Base: ${d['base']:>12,.0f}")
        print(f"      IVA:  ${d['impuesto']:>12,.0f}")
        print(f"      Total:${d['total']:>12,.0f}")
    except ErrorSistema as e:
        print(f"  ERROR  {e}")
    finally:
        Logger.info("OP05 finalizada")
    return reserva


def op06_reserva_fallida():
    _sep(6, "RESERVA FALLIDA — SERVICIO NO DISPONIBLE")
    try:
        s_ocupado = ReservaSala(20, "Sala VIP", 80_000, False)
        c         = Cliente(21, "Juan Medina", "10998877", "juan@test.com")
        r = Reserva(2, c, s_ocupado, 2)
        print(f"  INESPERADO  {r.describir()}")
    except ServicioNoDisponibleError as e:
        print(f"  CAPTURADO  ServicioNoDisponibleError → {e}")
    except DatoInvalidoError as e:
        print(f"  CAPTURADO  DatoInvalidoError → {e}")
    except ErrorSistema as e:
        print(f"  ERROR  {e}")
    else:
        Logger.warn("OP06: se esperaba una excepción pero no ocurrió")
    finally:
        Logger.info("OP06 finalizada — validación de disponibilidad confirmada")
        print("    [finally] OP06 cerrada correctamente")


def op07_cancelacion_reserva(reserva: Reserva):
    _sep(7, "CANCELACIÓN DE RESERVA + ENCADENAMIENTO")
    if reserva is None:
        print("  AVISO  Reserva no disponible (op05 falló); se omite cancelación.")
        Logger.warn("OP07 saltada: reserva es None")
        return

    # Cancelación válida
    try:
        reserva.cancelar("Cambio de agenda")
        print(f"  OK  Cancelada: {reserva.describir()}")
    except OperacionNoPermitidaError as e:
        print(f"  ERROR  {e}")

    # Segundo intento de cancelación → encadenamiento de excepciones
    print("\n  Intentando cancelar nuevamente (debe fallar):")
    try:
        reserva.cancelar("Segundo intento")
    except OperacionNoPermitidaError as causa:
        wrapped = ReservaInvalidaError(f"Cancelación duplicada detectada")
        raise wrapped from causa
    except ReservaInvalidaError as final:
        print(f"  ENCADENADO  ReservaInvalidaError")
        print(f"    └─ causa: {final.__cause__}")
        Logger.error(f"Encadenamiento: {final} ← {final.__cause__}")


def op08_calculo_costos_sobrecargado():
    _sep(8, "CÁLCULO DE COSTOS — MÉTODOS SOBRECARGADOS")
    try:
        c = Cliente(30, "Ana Morales", "1111222", "ana@test.com")
        s = Asesoria(30, "Asesoría Contable", 120_000, True)
        r = Reserva(3, c, s, 2)

        t0 = r.calcular_total()
        t1 = r.calcular_total(0.19)
        t2 = r.calcular_total(0.19, 20_000)
        t3 = r.calcular_total(0.0,  10_000)

        print(f"  Costo base:                      ${t0:>12,.0f}")
        print(f"  Con 19% IVA:                     ${t1:>12,.0f}")
        print(f"  Con 19% IVA  - $20.000 desc.:    ${t2:>12,.0f}")
        print(f"  Sin impuesto - $10.000 desc.:     ${t3:>12,.0f}")

        print(f"\n  Desglose completo (19% IVA, $20k desc.):")
        for k, v in r.calcular_desglose(0.19, 20_000).items():
            print(f"    {k:<12}: {v:,.0f}" if isinstance(v, float) else f"    {k:<12}: {v}")
    except CalculoInconsistenteError as e:
        print(f"  ERROR  {e}")
    except ErrorSistema as e:
        print(f"  ERROR  {e}")


def op09_try_except_else_finally():
    _sep(9, "PATRONES try/except/else/finally + ENCADENAMIENTO")

    # — Patrón try/except/else/finally
    print("  Patrón try / except / else / finally:")
    try:
        c = Cliente(40, "Luis Torres", "5566778", "luis@test.com")
        s = AlquilerEquipo(40, "Drone DJI", 45_000, True)
        r = Reserva(4, c, s, 5)
        r.confirmar()
    except DatoInvalidoError as e:
        print(f"    except DatoInvalidoError: {e}")
    except ServicioNoDisponibleError as e:
        print(f"    except ServicioNoDisponibleError: {e}")
    except ErrorSistema as e:
        print(f"    except ErrorSistema: {e}")
    else:
        print(f"    else (sin errores): {r.describir()}")
        Logger.info("OP09: reserva completada en bloque else")
    finally:
        print(f"    finally: bloque ejecutado siempre")
        Logger.info("OP09: bloque finally ejecutado")

    # — Encadenamiento de excepciones
    print("\n  Encadenamiento de excepciones:")
    try:
        try:
            raise DatoInvalidoError("campo_prueba", "valor_invalido_99")
        except DatoInvalidoError as original:
            raise OperacionNoPermitidaError("procesar", "error") from original
    except OperacionNoPermitidaError as final:
        print(f"    Excepción final  : {type(final).__name__}: {final}")
        print(f"    Causa encadenada : {type(final.__cause__).__name__}: {final.__cause__}")
        Logger.error(f"Encadenamiento demostrado: {final} ← {final.__cause__}")

    # — Lanzamiento desde bloque except con raise
    print("\n  Re-lanzamiento con raise:")
    try:
        try:
            c2 = Cliente(50, "", "12345678", "ok@ok.com")
        except DatoInvalidoError:
            Logger.warn("OP09: re-lanzando excepción enriquecida")
            raise ErrorSistema("Datos de cliente rechazados por el sistema", "E010")
    except ErrorSistema as e:
        print(f"    Re-lanzado: [{e.codigo}] {e}")


def op10_error_critico_y_recuperacion():
    _sep(10, "ERROR CRÍTICO Y RECUPERACIÓN DEL SISTEMA")
    print("  El sistema procesa lotes mixtos de datos y NO se detiene ante errores.\n")

    lote = [
        (60, "Sandra Ríos",   "9988776",  "sandra@correo.com"),
        (61, "X",             "123",      "mailroto"),
        (62, "Andrés Paz",    "1122334",  "andres@correo.com"),
        (63, "",              "9876543",  "empty@test.com"),
        (64, "Laura Cano",    "7654321",  "laura@valid.com"),
        (65, "Miguel Torres", "4433221",  "miguel"),
        (66, "Carmen Vega",   "3344556",  "carmen@vega.co"),
        (67, "T",             "12345",    "t@t.co"),
    ]

    exitosos = 0
    for id_c, nombre, doc, correo in lote:
        try:
            c = Cliente(id_c, nombre, doc, correo)
            print(f"  OK  [{id_c}] {c.get_nombre()}")
            exitosos += 1
        except DatoInvalidoError as e:
            print(f"  FALLO  [{id_c}] {e}")
            Logger.warn(f"OP10: cliente {id_c} rechazado")
        except ErrorSistema as e:
            print(f"  CRITICO  [{id_c}] [{e.codigo}] {e}")
            Logger.critico(f"OP10: error crítico en cliente {id_c}: {e}")
        finally:
            pass  # el sistema siempre continúa

    total = len(lote)
    print(f"\n  Resumen del lote:")
    print(f"    Procesados : {total}")
    print(f"    Exitosos   : {exitosos}")
    print(f"    Fallidos   : {total - exitosos}")
    print(f"\n  Estado global del sistema:")
    print(f"    Clientes registrados : {Cliente.total()}")
    print(f"    Reservas en sistema  : {Reserva.total()}")
    Logger.info(
        f"OP10 completada: {exitosos}/{total} exitosos. "
        f"Clientes={Cliente.total()} Reservas={Reserva.total()}"
    )


# ─── Punto de entrada ─────────────────────────────────────────
if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════╗")
    print("║     OPERACIÓN 09 — MANEJO DE EXCEPCIONES Y LOGS          ║")
    print("╚══════════════════════════════════════════════════════════╝")
    Logger.info("=" * 45 + " INICIO SESIÓN " + "=" * 45)

    op01_registro_cliente_valido()
    op02_registro_cliente_invalido()
    op03_creacion_servicios_validos()
    op04_creacion_servicio_invalido()

    # Datos compartidos para op05 → op07
    cliente_main  = Cliente(100, "Diego Vargas",  "3344556", "diego@main.com")
    servicio_main = ReservaSala(100, "Sala Ejecutiva", 60_000, True)

    reserva_main = op05_reserva_exitosa(cliente_main, servicio_main)
    op06_reserva_fallida()

    try:
        op07_cancelacion_reserva(reserva_main)
    except ReservaInvalidaError as e:
        print(f"  [main] Excepción encadenada capturada: {e}")
        if e.__cause__:
            print(f"         Causa original: {e.__cause__}")

    op08_calculo_costos_sobrecargado()
    op09_try_except_else_finally()
    op10_error_critico_y_recuperacion()

    print(f"\n{'=' * 60}")
    print(f"  FIN DE EJECUCIÓN | Log: {Logger.ARCHIVO}")
    print(f"{'=' * 60}\n")
    Logger.info("=" * 45 + " FIN SESIÓN " + "=" * 45)
