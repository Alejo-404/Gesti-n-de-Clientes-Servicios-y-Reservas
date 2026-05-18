# ============================================================
# OPERACIÓN 10 - VALIDACIONES DEL SISTEMA
# Sistema de Gestión de Clientes, Servicios y Reservas
# ============================================================
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from abc import ABC, abstractmethod
from datetime import datetime
import re


# ─── Logger ──────────────────────────────────────────────────
class Logger:
    ARCHIVO = "validaciones_sistema.log"

    @staticmethod
    def registrar(nivel: str, mensaje: str):
        try:
            ts   = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            linea = f"[{nivel.upper():<8}] {ts} | {mensaje}\n"
            with open(Logger.ARCHIVO, "a", encoding="utf-8") as f:
                f.write(linea)
        except OSError:
            pass

    @classmethod
    def info(cls, msg):  cls.registrar("INFO",    msg)
    @classmethod
    def error(cls, msg): cls.registrar("ERROR",   msg)
    @classmethod
    def warn(cls, msg):  cls.registrar("WARNING", msg)


# ─── Excepciones ─────────────────────────────────────────────
class ErrorSistema(Exception):
    def __init__(self, mensaje: str, codigo: str = "E000"):
        super().__init__(mensaje)
        self.codigo = codigo
        Logger.error(f"[{codigo}] {mensaje}")


class DatoInvalidoError(ErrorSistema):
    def __init__(self, campo: str, detalle: str = ""):
        msg = f"Campo inválido: '{campo}'" + (f" → {detalle}" if detalle else "")
        super().__init__(msg, "E001")
        self.campo = campo


class ParametroFaltanteError(ErrorSistema):
    def __init__(self, param: str):
        super().__init__(f"Parámetro faltante: '{param}'", "E002")


class ServicioNoDisponibleError(ErrorSistema):
    def __init__(self, servicio: str):
        super().__init__(f"Servicio no disponible: '{servicio}'", "E003")


class ReservaInvalidaError(ErrorSistema):
    def __init__(self, motivo: str):
        super().__init__(f"Reserva inválida: {motivo}", "E004")


class OperacionNoPermitidaError(ErrorSistema):
    def __init__(self, op: str, estado: str):
        super().__init__(f"Operación '{op}' no permitida en estado '{estado}'", "E005")


class CalculoInconsistenteError(ErrorSistema):
    def __init__(self, detalle: str):
        super().__init__(f"Cálculo inconsistente: {detalle}", "E006")


class ValidacionFallidaError(ErrorSistema):
    def __init__(self, regla: str, valor=None):
        msg = f"Regla incumplida: {regla}" + (f" (valor={valor})" if valor is not None else "")
        super().__init__(msg, "E007")
        self.regla = regla


# ─── Validadores (jerarquía abstracta) ───────────────────────
class Validador(ABC):
    @abstractmethod
    def validar(self, datos: dict) -> list:
        pass

    def es_valido(self, datos: dict) -> bool:
        return len(self.validar(datos)) == 0


class ValidadorCliente(Validador):
    _RE_CORREO    = re.compile(r"^[\w\.\-]+@[\w\.\-]+\.\w{2,}$")
    _RE_DOCUMENTO = re.compile(r"^\d{7,12}$")
    _RE_TELEFONO  = re.compile(r"^\d{7,15}$")

    def validar(self, datos: dict) -> list:
        errores = []
        nombre = datos.get("nombre", "")
        if not nombre or not str(nombre).strip():
            errores.append("Nombre vacío o nulo")
        elif len(str(nombre).strip()) < 3:
            errores.append(f"Nombre demasiado corto: '{nombre}' (mínimo 3 caracteres)")
        elif len(str(nombre).strip()) > 100:
            errores.append(f"Nombre excede 100 caracteres")

        doc = str(datos.get("documento", ""))
        if not self._RE_DOCUMENTO.match(doc):
            errores.append(f"Documento inválido: '{doc}' (7-12 dígitos)")

        correo = str(datos.get("correo", ""))
        if not self._RE_CORREO.match(correo):
            errores.append(f"Correo inválido: '{correo}'")

        tel = str(datos.get("telefono", ""))
        if tel and not self._RE_TELEFONO.match(tel):
            errores.append(f"Teléfono inválido: '{tel}' (7-15 dígitos)")
        return errores


class ValidadorServicio(Validador):
    TIPOS_VALIDOS = {"ReservaSala", "AlquilerEquipo", "Asesoria"}
    PRECIO_MIN    = 1_000
    PRECIO_MAX    = 10_000_000

    def validar(self, datos: dict) -> list:
        errores = []
        nombre = str(datos.get("nombre", "")).strip()
        if not nombre:
            errores.append("Nombre del servicio vacío")
        elif len(nombre) > 80:
            errores.append(f"Nombre del servicio excede 80 caracteres")

        try:
            precio = float(datos.get("precio_base", 0))
            if precio < self.PRECIO_MIN:
                errores.append(f"Precio muy bajo: ${precio:,.0f} (mínimo ${self.PRECIO_MIN:,})")
            if precio > self.PRECIO_MAX:
                errores.append(f"Precio excesivo: ${precio:,.0f} (máximo ${self.PRECIO_MAX:,})")
        except (TypeError, ValueError):
            errores.append(f"Precio no numérico: '{datos.get('precio_base')}'")

        tipo = datos.get("tipo", "")
        if tipo and tipo not in self.TIPOS_VALIDOS:
            errores.append(
                f"Tipo de servicio inválido: '{tipo}' — "
                f"válidos: {', '.join(sorted(self.TIPOS_VALIDOS))}"
            )
        return errores


class ValidadorReserva(Validador):
    DUR_MIN = 1
    DUR_MAX = 24

    def validar(self, datos: dict) -> list:
        errores = []
        dur = datos.get("duracion")
        if dur is None:
            errores.append("Duración no especificada")
        else:
            try:
                dur = int(dur)
                if dur < self.DUR_MIN:
                    errores.append(f"Duración mínima: {self.DUR_MIN}h (recibido: {dur})")
                if dur > self.DUR_MAX:
                    errores.append(f"Duración máxima: {self.DUR_MAX}h (recibido: {dur})")
            except (TypeError, ValueError):
                errores.append(f"Duración no entera: '{dur}'")

        cid = datos.get("cliente_id")
        if not isinstance(cid, int) or cid <= 0:
            errores.append(f"ID de cliente inválido: '{cid}'")

        sid = datos.get("servicio_id")
        if not isinstance(sid, int) or sid <= 0:
            errores.append(f"ID de servicio inválido: '{sid}'")

        if not datos.get("servicio_disponible", True):
            errores.append("El servicio seleccionado no está disponible")
        return errores


class ValidadorCalculo(Validador):
    def validar(self, datos: dict) -> list:
        errores = []
        try:
            tasa = float(datos.get("tasa_impuesto", 0))
            if not (0.0 <= tasa <= 1.0):
                errores.append(f"Tasa de impuesto fuera de rango [0–1]: {tasa}")
        except (TypeError, ValueError):
            errores.append(f"Tasa de impuesto no numérica: '{datos.get('tasa_impuesto')}'")

        try:
            desc = float(datos.get("descuento", 0))
            if desc < 0:
                errores.append(f"Descuento negativo: ${desc:,.0f}")
            base = datos.get("costo_base")
            if base is not None:
                base = float(base)
                if desc > base:
                    errores.append(
                        f"Descuento (${desc:,.0f}) supera costo base (${base:,.0f})"
                    )
        except (TypeError, ValueError):
            errores.append(f"Descuento no numérico: '{datos.get('descuento')}'")
        return errores


# ─── Entidad Base ─────────────────────────────────────────────
class Entidad(ABC):
    def __init__(self, id: int):
        if not isinstance(id, int) or id <= 0:
            raise DatoInvalidoError("id", "debe ser entero positivo")
        self._id = id

    def get_id(self) -> int:
        return self._id

    @abstractmethod
    def describir(self) -> str:
        pass


# ─── Cliente ──────────────────────────────────────────────────
class Cliente(Entidad):
    _validador: Validador = ValidadorCliente()
    _registro:  list      = []

    def __init__(self, id: int, nombre: str, documento: str, correo: str, telefono: str = ""):
        super().__init__(id)
        datos   = {"nombre": nombre, "documento": documento, "correo": correo, "telefono": telefono}
        errores = self._validador.validar(datos)
        if errores:
            detalle = " | ".join(errores)
            raise DatoInvalidoError("datos_cliente", detalle)
        self.__nombre    = str(nombre).strip()
        self.__documento = str(documento).strip()
        self.__correo    = str(correo).strip().lower()
        self.__telefono  = str(telefono).strip()
        Cliente._registro.append(self)
        Logger.info(f"Cliente registrado: #{id} {self.__nombre} ({self.__documento})")

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
    _validador: Validador = ValidadorServicio()

    def __init__(self, id: int, nombre: str, precio_base: float, disponible: bool = True):
        super().__init__(id)
        datos   = {"nombre": nombre, "precio_base": precio_base, "tipo": type(self).__name__}
        errores = self._validador.validar(datos)
        if errores:
            detalle = " | ".join(errores)
            raise DatoInvalidoError("datos_servicio", detalle)
        self.__nombre      = str(nombre).strip()
        self.__precio_base = float(precio_base)
        self.__disponible  = disponible
        Logger.info(f"Servicio creado: {type(self).__name__} #{id} '{self.__nombre}'")

    def get_nombre(self)      -> str:   return self.__nombre
    def get_precio_base(self) -> float: return self.__precio_base
    def esta_disponible(self) -> bool:  return self.__disponible
    def set_disponibilidad(self, estado: bool): self.__disponible = estado

    @abstractmethod
    def calcular_costo(self, duracion: int) -> float:
        pass

    @abstractmethod
    def describir(self) -> str:
        pass


class ReservaSala(Servicio):
    def calcular_costo(self, duracion: int) -> float:
        return self.get_precio_base() * duracion * 1.10

    def describir(self) -> str:
        return f"[Sala]   {self.get_nombre()} | ${self.get_precio_base():>10,.0f}/hr"


class AlquilerEquipo(Servicio):
    def calcular_costo(self, duracion: int) -> float:
        return self.get_precio_base() * duracion * 0.95

    def describir(self) -> str:
        return f"[Equipo] {self.get_nombre()} | ${self.get_precio_base():>10,.0f}/hr"


class Asesoria(Servicio):
    def calcular_costo(self, duracion: int) -> float:
        return self.get_precio_base() * duracion * 1.50

    def describir(self) -> str:
        return f"[Asesor] {self.get_nombre()} | ${self.get_precio_base():>10,.0f}/hr"


# ─── Reserva ──────────────────────────────────────────────────
class Reserva(Entidad):
    _validador:       Validador = ValidadorReserva()
    _calc_validador:  Validador = ValidadorCalculo()
    _historial:       list      = []

    # Tabla de transiciones válidas por estado
    TRANSICIONES = {
        "pendiente":  {"confirmar", "cancelar"},
        "confirmada": {"cancelar",  "finalizar"},
        "cancelada":  set(),
        "finalizada": set(),
    }

    def __init__(self, id: int, cliente: Cliente, servicio: Servicio, duracion: int):
        super().__init__(id)
        datos = {
            "cliente_id":          cliente.get_id() if isinstance(cliente, Cliente) else None,
            "servicio_id":         servicio.get_id() if isinstance(servicio, Servicio) else None,
            "duracion":            duracion,
            "servicio_disponible": servicio.esta_disponible() if isinstance(servicio, Servicio) else False,
        }
        errores = self._validador.validar(datos)
        if errores:
            detalle = " | ".join(errores)
            Logger.error(f"Reserva rechazada: {detalle}")
            raise ReservaInvalidaError(detalle)

        self.__cliente  = cliente
        self.__servicio = servicio
        self.__duracion = duracion
        self.__estado   = "pendiente"
        self.__fecha    = datetime.now()
        self.__codigo   = f"RES-{id:04d}-{self.__fecha.strftime('%Y%m%d%H%M%S')}"
        Reserva._historial.append(self)
        Logger.info(f"Reserva creada: {self.__codigo}")

    def _verificar_transicion(self, operacion: str):
        if operacion not in self.TRANSICIONES.get(self.__estado, set()):
            raise OperacionNoPermitidaError(operacion, self.__estado)

    def confirmar(self) -> bool:
        try:
            self._verificar_transicion("confirmar")
            costo   = self.__servicio.calcular_costo(self.__duracion)
            errores = self._calc_validador.validar({"tasa_impuesto": 0, "costo_base": costo})
            if errores:
                raise CalculoInconsistenteError(" | ".join(errores))
            self.__estado = "confirmada"
            Logger.info(f"Reserva confirmada: {self.__codigo} | ${costo:,.0f}")
            return True
        except (OperacionNoPermitidaError, CalculoInconsistenteError):
            raise
        except Exception as e:
            raise ReservaInvalidaError(f"Fallo confirmación: {e}") from e
        finally:
            Logger.info(f"  [finally] confirmar() — estado: {self.__estado}")

    def cancelar(self, motivo: str = "No especificado") -> bool:
        try:
            self._verificar_transicion("cancelar")
            self.__estado = "cancelada"
            self.__servicio.set_disponibilidad(True)
            Logger.info(f"Reserva cancelada: {self.__codigo} | {motivo}")
            return True
        except OperacionNoPermitidaError:
            raise
        finally:
            Logger.info(f"  [finally] cancelar() — estado: {self.__estado}")

    def finalizar(self) -> bool:
        try:
            self._verificar_transicion("finalizar")
            self.__estado = "finalizada"
            self.__servicio.set_disponibilidad(True)
            Logger.info(f"Reserva finalizada: {self.__codigo}")
            return True
        except OperacionNoPermitidaError:
            raise

    # Método sobrecargado: sin args, con impuesto, con impuesto+descuento
    def calcular_total(self, tasa_impuesto: float = 0.0, descuento: float = 0.0) -> float:
        base    = self.__servicio.calcular_costo(self.__duracion)
        errores = self._calc_validador.validar({
            "tasa_impuesto": tasa_impuesto,
            "descuento":     descuento,
            "costo_base":    base,
        })
        if errores:
            raise CalculoInconsistenteError(" | ".join(errores))
        return max(0.0, base * (1 + tasa_impuesto) - descuento)

    def describir(self) -> str:
        return (f"Reserva {self.__codigo} | {self.__cliente.get_nombre()} | "
                f"{self.__servicio.get_nombre()} | {self.__duracion}h | "
                f"{self.__estado.upper()}")

    def get_codigo(self) -> str: return self.__codigo
    def get_estado(self) -> str: return self.__estado

    @classmethod
    def total(cls) -> int:
        return len(cls._historial)


# ─── Coordinador central de validaciones ─────────────────────
class ValidadorSistema:
    def __init__(self):
        self._c_v = ValidadorCliente()
        self._s_v = ValidadorServicio()
        self._r_v = ValidadorReserva()
        self._k_v = ValidadorCalculo()
        self._bitacora: list = []

    def _log(self, operacion: str, valido: bool, errores: list):
        entrada = {
            "ts":      datetime.now().strftime("%H:%M:%S"),
            "op":      operacion,
            "valido":  valido,
            "errores": errores,
        }
        self._bitacora.append(entrada)
        nivel = "INFO" if valido else "ERROR"
        msg   = f"[{operacion}] {'OK' if valido else 'FALLO: ' + ' | '.join(errores)}"
        Logger.registrar(nivel, msg)
        return entrada

    def validar_cliente(self, datos: dict) -> tuple:
        e = self._c_v.validar(datos)
        self._log("ValidarCliente",  not e, e)
        return not e, e

    def validar_servicio(self, datos: dict) -> tuple:
        e = self._s_v.validar(datos)
        self._log("ValidarServicio", not e, e)
        return not e, e

    def validar_reserva(self, datos: dict) -> tuple:
        e = self._r_v.validar(datos)
        self._log("ValidarReserva",  not e, e)
        return not e, e

    def validar_calculo(self, datos: dict) -> tuple:
        e = self._k_v.validar(datos)
        self._log("ValidarCalculo",  not e, e)
        return not e, e

    def resumen(self) -> dict:
        total    = len(self._bitacora)
        exitosas = sum(1 for e in self._bitacora if e["valido"])
        return {
            "total":       total,
            "exitosas":    exitosas,
            "fallidas":    total - exitosas,
            "tasa_exito":  f"{exitosas / total * 100:.1f}%" if total else "N/A",
        }


# ─── Instancia global del coordinador ────────────────────────
sv = ValidadorSistema()


# ─── Utilidades de presentación ──────────────────────────────
def _sep(num: int, titulo: str):
    linea = "=" * 60
    print(f"\n{linea}")
    print(f"  OPERACIÓN {num:02d}: {titulo}")
    print(linea)
    Logger.info(f"{'─'*15} OPERACIÓN {num:02d}: {titulo} {'─'*15}")


def _mostrar(valido: bool, errores: list, etiqueta: str = ""):
    if valido:
        print(f"  OK   Validación exitosa" + (f": {etiqueta}" if etiqueta else ""))
    else:
        print(f"  FALLO  Validación rechazada{' (' + etiqueta + ')' if etiqueta else ''}:")
        for err in errores:
            print(f"    • {err}")


# ─── Las 10 Operaciones ───────────────────────────────────────

def op01_cliente_valido():
    _sep(1, "VALIDAR CLIENTE VÁLIDO")
    datos  = {"nombre": "María López", "documento": "10987654", "correo": "maria@correo.com", "telefono": "3001234567"}
    valido, errores = sv.validar_cliente(datos)
    _mostrar(valido, errores, datos["nombre"])
    if valido:
        try:
            c = Cliente(1, datos["nombre"], datos["documento"], datos["correo"], datos["telefono"])
            print(f"    Objeto creado: {c.describir()}")
        except ErrorSistema as e:
            print(f"    ERROR al instanciar: {e}")


def op02_cliente_invalido():
    _sep(2, "VALIDAR CLIENTES INVÁLIDOS — MÚLTIPLES ERRORES")
    casos = [
        ({"nombre": "",       "documento": "12345678", "correo": "ok@mail.com"},         "Nombre vacío"),
        ({"nombre": "AB",     "documento": "12345678", "correo": "ok@mail.com"},         "Nombre < 3 chars"),
        ({"nombre": "Carlos", "documento": "abc",      "correo": "correo-invalido"},     "Doc + correo malos"),
        ({"nombre": "P" * 110,"documento": "12345678", "correo": "ok@ok.com"},           "Nombre excede 100 chars"),
        ({"nombre": "Ana",    "documento": "12345678", "correo": "ok@ok.com",
          "telefono": "123abc"}, "Teléfono no numérico"),
    ]
    for datos, desc in casos:
        print(f"\n  Caso — {desc}:")
        valido, errores = sv.validar_cliente(datos)
        _mostrar(valido, errores)


def op03_servicio_valido():
    _sep(3, "VALIDAR SERVICIO VÁLIDO")
    casos_validos = [
        {"nombre": "Sala Principal",       "precio_base": 50_000,  "tipo": "ReservaSala"},
        {"nombre": "Proyector HD",         "precio_base": 20_000,  "tipo": "AlquilerEquipo"},
        {"nombre": "Consultoría Jurídica", "precio_base": 150_000, "tipo": "Asesoria"},
    ]
    for datos in casos_validos:
        valido, errores = sv.validar_servicio(datos)
        _mostrar(valido, errores, datos["nombre"])
        if valido:
            tipo_cls = {"ReservaSala": ReservaSala, "AlquilerEquipo": AlquilerEquipo, "Asesoria": Asesoria}
            try:
                idx = casos_validos.index(datos) + 1
                s   = tipo_cls[datos["tipo"]](idx, datos["nombre"], datos["precio_base"], True)
                print(f"    Objeto creado: {s.describir()}")
            except ErrorSistema as e:
                print(f"    ERROR al instanciar: {e}")


def op04_servicio_invalido():
    _sep(4, "VALIDAR SERVICIOS INVÁLIDOS — PARÁMETROS FUERA DE RANGO")
    casos = [
        ({"nombre": "",          "precio_base": 50_000,       "tipo": "ReservaSala"},     "Nombre vacío"),
        ({"nombre": "Test",      "precio_base": -100,         "tipo": "AlquilerEquipo"},  "Precio negativo"),
        ({"nombre": "Test",      "precio_base": 50_000_000,   "tipo": "Asesoria"},        "Precio excesivo"),
        ({"nombre": "Test",      "precio_base": "no-numerico","tipo": "ReservaSala"},     "Precio no numérico"),
        ({"nombre": "Test",      "precio_base": 20_000,       "tipo": "TipoFalso"},       "Tipo desconocido"),
        ({"nombre": "X" * 85,   "precio_base": 30_000,       "tipo": "ReservaSala"},     "Nombre excede 80 chars"),
    ]
    for datos, desc in casos:
        print(f"\n  Caso — {desc}:")
        valido, errores = sv.validar_servicio(datos)
        _mostrar(valido, errores)


def op05_reserva_valida():
    _sep(5, "VALIDAR RESERVA VÁLIDA")
    datos  = {"cliente_id": 1, "servicio_id": 1, "duracion": 3, "servicio_disponible": True}
    valido, errores = sv.validar_reserva(datos)
    _mostrar(valido, errores, f"duración={datos['duracion']}h")
    if valido:
        try:
            c = Cliente(5, "Carlos Ruiz", "20334455", "carlos@mail.com")
            s = AlquilerEquipo(5, "Proyector HD", 30_000, True)
            r = Reserva(5, c, s, 3)
            r.confirmar()
            print(f"    Objeto creado: {r.describir()}")
            print(f"    Total (19% IVA): ${r.calcular_total(0.19):,.0f}")
        except ErrorSistema as e:
            print(f"    ERROR: {e}")


def op06_reserva_duracion_extrema():
    _sep(6, "VALIDAR RESERVA — DURACIÓN FUERA DE RANGO")
    casos = [
        {"cliente_id": 1, "servicio_id": 1, "duracion": 0,    "servicio_disponible": True},
        {"cliente_id": 1, "servicio_id": 1, "duracion": 25,   "servicio_disponible": True},
        {"cliente_id": 1, "servicio_id": 1, "duracion": -3,   "servicio_disponible": True},
        {"cliente_id": 1, "servicio_id": 1, "duracion": "dos","servicio_disponible": True},
        {"cliente_id": 1, "servicio_id": 1, "duracion": 8,    "servicio_disponible": False},
    ]
    for datos in casos:
        print(f"\n  Caso — duración={datos['duracion']}, disponible={datos['servicio_disponible']}:")
        valido, errores = sv.validar_reserva(datos)
        _mostrar(valido, errores)


def op07_calculo_costos():
    _sep(7, "VALIDAR CONSISTENCIA DE CÁLCULO DE COSTOS")
    casos = [
        ({"tasa_impuesto": 0.19, "descuento": 10_000, "costo_base": 100_000}, "Válido — 19% IVA, $10k desc."),
        ({"tasa_impuesto": 0.0,  "descuento": 0,      "costo_base": 50_000},  "Válido — sin impuesto ni desc."),
        ({"tasa_impuesto": 1.5,  "descuento": 0,      "costo_base": 50_000},  "Tasa > 100%"),
        ({"tasa_impuesto": 0.1,  "descuento": -500,   "costo_base": 50_000},  "Descuento negativo"),
        ({"tasa_impuesto": 0.19, "descuento": 200_000,"costo_base": 50_000},  "Descuento > base"),
        ({"tasa_impuesto": "X",  "descuento": 0,      "costo_base": 50_000},  "Tasa no numérica"),
    ]
    for datos, desc in casos:
        print(f"\n  Caso — {desc}:")
        valido, errores = sv.validar_calculo(datos)
        _mostrar(valido, errores)
        if valido:
            base  = float(datos["costo_base"])
            total = base * (1 + float(datos["tasa_impuesto"])) - float(datos["descuento"])
            print(f"    Total calculado: ${max(0.0, total):,.0f}")


def op08_transiciones_estado():
    _sep(8, "VALIDAR TRANSICIONES DE ESTADO DE RESERVA")
    try:
        c = Cliente(8, "Sofía Herrera", "34556677", "sofia@mail.com")
        s = ReservaSala(8, "Sala VIP", 80_000, True)
        r = Reserva(8, c, s, 2)
        print(f"  Estado inicial: {r.get_estado().upper()}")

        for operacion, fn, esperado_ok in [
            ("confirmar",           r.confirmar, True),
            ("confirmar (repetir)", r.confirmar, False),
            ("cancelar",            r.cancelar,  True),
            ("cancelar (repetir)",  r.cancelar,  False),
        ]:
            try:
                resultado = fn()
                if esperado_ok:
                    print(f"  OK   {operacion}() → {r.get_estado().upper()}")
                else:
                    print(f"  AVISO  {operacion}() debía fallar pero no falló")
            except OperacionNoPermitidaError as e:
                if not esperado_ok:
                    print(f"  OK   Transición inválida rechazada: {operacion}() → {e}")
                else:
                    print(f"  ERROR  {e}")
    except ErrorSistema as e:
        print(f"  ERROR  {e}")


def op09_reglas_negocio():
    _sep(9, "VALIDAR REGLAS DE NEGOCIO DEL SISTEMA")

    print("  Regla 1: Servicio no disponible no puede reservarse")
    try:
        c  = Cliente(9,  "Ricardo Blanco", "55667788", "ricardo@mail.com")
        s  = Asesoria(9, "Asesoría Fiscal", 200_000, False)
        r  = Reserva(9,  c, s, 1)
        print(f"  AVISO  Reserva creada (debía rechazarse): {r.describir()}")
    except ReservaInvalidaError as e:
        print(f"  OK   Regla aplicada: {e}")

    print("\n  Regla 2: Descuento no puede superar el costo base")
    try:
        c2 = Cliente(91, "Elena Mora",  "66778899", "elena@mail.com")
        s2 = AlquilerEquipo(91, "Cámara Pro", 25_000, True)
        r2 = Reserva(91, c2, s2, 1)
        total = r2.calcular_total(tasa_impuesto=0.0, descuento=500_000)
        print(f"  AVISO  Total = ${total:,.0f} (descuento mayor que base debía rechazarse)")
    except CalculoInconsistenteError as e:
        print(f"  OK   Regla aplicada: {e}")

    print("\n  Regla 3: ID negativo o cero rechazado")
    try:
        c3 = Cliente(-1, "Ghost User", "12345678", "ghost@mail.com")
        print(f"  AVISO  Cliente creado con ID inválido")
    except DatoInvalidoError as e:
        print(f"  OK   Regla aplicada: {e}")

    print("\n  Regla 4: Encadenamiento — validación fallida escala como ReservaInvalidaError")
    try:
        try:
            datos = {"cliente_id": None, "servicio_id": 1, "duracion": 2, "servicio_disponible": True}
            valido, errores = sv.validar_reserva(datos)
            if not valido:
                raise ValidacionFallidaError("ID de cliente nulo", None)
        except ValidacionFallidaError as ve:
            raise ReservaInvalidaError(f"Datos incompletos para crear reserva") from ve
    except ReservaInvalidaError as final:
        print(f"  OK   Encadenado: {type(final).__name__}: {final}")
        print(f"       Causa: {type(final.__cause__).__name__}: {final.__cause__}")


def op10_resumen_sistema():
    _sep(10, "RESUMEN Y ESTADO GLOBAL DEL SISTEMA")
    resumen = sv.resumen()
    print(f"  Validaciones ejecutadas en esta sesión:")
    print(f"    Total      : {resumen['total']}")
    print(f"    Exitosas   : {resumen['exitosas']}")
    print(f"    Fallidas   : {resumen['fallidas']}")
    print(f"    Tasa éxito : {resumen['tasa_exito']}")
    print(f"\n  Entidades creadas:")
    print(f"    Clientes registrados : {Cliente.total()}")
    print(f"    Reservas en sistema  : {Reserva.total()}")
    Logger.info(
        f"Sesión completada — validaciones: {resumen['total']} "
        f"({resumen['exitosas']} OK / {resumen['fallidas']} FALLO) | "
        f"Clientes={Cliente.total()} Reservas={Reserva.total()}"
    )


# ─── Punto de entrada ─────────────────────────────────────────
if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════╗")
    print("║     OPERACIÓN 10 — VALIDACIONES DEL SISTEMA              ║")
    print("╚══════════════════════════════════════════════════════════╝")
    Logger.info("=" * 45 + " INICIO SESIÓN " + "=" * 45)

    op01_cliente_valido()
    op02_cliente_invalido()
    op03_servicio_valido()
    op04_servicio_invalido()
    op05_reserva_valida()
    op06_reserva_duracion_extrema()
    op07_calculo_costos()
    op08_transiciones_estado()
    op09_reglas_negocio()
    op10_resumen_sistema()

    print(f"\n{'=' * 60}")
    print(f"  FIN DE EJECUCIÓN | Log: {Logger.ARCHIVO}")
    print(f"{'=' * 60}\n")
    Logger.info("=" * 45 + " FIN SESIÓN " + "=" * 45)
