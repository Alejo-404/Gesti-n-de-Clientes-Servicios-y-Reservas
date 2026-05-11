from abc import ABC, abstractmethod
from datetime import datetime

# ==============================================
# CLASES BASE (Compañeros)
# ==============================================
class Entidad(ABC):
    def __init__(self, id: int):
        self._id = id
    def get_id(self):
        return self._id

# Excepciones base
class ErrorSistema(Exception): pass
class DatoInvalidoError(ErrorSistema): pass
class ParametroFaltanteError(ErrorSistema): pass
class ServicioNoDisponibleError(ErrorSistema): pass
class ReservaInvalidaError(ErrorSistema): pass
class OperacionNoPermitidaError(ErrorSistema): pass
class CalculoInconsistenteError(ErrorSistema): pass

# Cliente
class Cliente(Entidad):
    def __init__(self, id: int, nombre: str, documento: str, correo: str):
        super().__init__(id)
        if not nombre or len(nombre) < 3:
            raise DatoInvalidoError("Nombre inválido")
        if not documento or len(documento) < 5:
            raise DatoInvalidoError("Documento inválido")
        if "@" not in correo:
            raise DatoInvalidoError("Correo inválido")
        self.__nombre = nombre
        self.__documento = documento
        self.__correo = correo
    def get_nombre(self): return self.__nombre
    def get_documento(self): return self.__documento
    def get_correo(self): return self.__correo

# Servicios
class Servicio(Entidad, ABC):
    def __init__(self, id: int, nombre: str, precio_base: float, disponible: bool):
        super().__init__(id)
        self.__nombre = nombre
        self.__precio_base = precio_base
        self.__disponible = disponible
    def get_nombre(self): return self.__nombre
    def get_precio_base(self): return self.__precio_base
    def esta_disponible(self): return self.__disponible
    def set_disponibilidad(self, estado: bool): self.__disponible = estado
    @abstractmethod
    def calcular_costo(self, duracion: int) -> float: pass

class ReservaSala(Servicio):
    def calcular_costo(self, duracion: int) -> float:
        return self.get_precio_base() * duracion * 1.1

class AlquilerEquipo(Servicio):
    def calcular_costo(self, duracion: int) -> float:
        return self.get_precio_base() * duracion * 0.95

class Asesoria(Servicio):
    def calcular_costo(self, duracion: int) -> float:
        return self.get_precio_base() * duracion * 1.5

# ==============================================
# ✅ CLASE RESERVA - SOLO LÓGICA EXITOSA
# ==============================================
class ReservaExitosa(Entidad):
    __cliente: Cliente
    __servicio: Servicio
    __duracion: int
    __estado: str
    __fecha_reserva: datetime
    __codigo_reserva: str
    _lista_reservas_exitosas = []

    def __init__(self, id: int, cliente: Cliente, servicio: Servicio, duracion: int):
        super().__init__(id)
        # SOLO VALIDACIONES CORRECTAS
        if not isinstance(cliente, Cliente):
            raise DatoInvalidoError("Cliente no válido")
        if not isinstance(servicio, Servicio):
            raise DatoInvalidoError("Servicio no válido")
        if duracion <= 0:
            raise ParametroFaltanteError("Duración debe ser mayor a 0")
        if not servicio.esta_disponible():
            raise ServicioNoDisponibleError("Servicio no disponible")

        # Asignación de datos correctos
        self.__cliente = cliente
        self.__servicio = servicio
        self.__duracion = duracion
        self.__estado = "pendiente"
        self.__fecha_reserva = datetime.now()
        self.__codigo_reserva = f"RES-EXIT-{id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # REGISTRO DE ÉXITO
        self._registrar_evento(f"✅ RESERVA EXITOSA CREADA | Código: {self.__codigo_reserva} | Cliente: {cliente.get_nombre()}")
        ReservaExitosa._lista_reservas_exitosas.append(self)

    # Confirmar reserva exitosamente
    def confirmar_reserva(self) -> bool:
        try:
            if self.__estado != "pendiente":
                raise OperacionNoPermitidaError("Ya fue procesada")
            costo = self.__servicio.calcular_costo(self.__duracion)
            if costo < 0:
                raise CalculoInconsistenteError("Costo inválido")
            
            self.__estado = "confirmada"
            self._registrar_evento(f"✅ RESERVA CONFIRMADA | Código: {self.__codigo_reserva} | Costo: ${costo:,}")
            return True
        except Exception as e:
            return False
        finally:
            self._registrar_evento(f"ℹ️ Proceso de confirmación finalizado")

    # Cancelar reserva (operación válida)
    def cancelar_reserva(self, motivo: str = "Sin motivo") -> bool:
        try:
            if self.__estado in ["cancelada"]:
                raise OperacionNoPermitidaError("Ya está cancelada")
            self.__estado = "cancelada"
            self.__servicio.set_disponibilidad(True)
            self._registrar_evento(f"🚫 RESERVA CANCELADA | Código: {self.__codigo_reserva} | Motivo: {motivo}")
            return True
        except:
            return False

    # Métodos sobrecargados para cálculo (versiones válidas)
    def calcular_total(self, *args) -> float:
        costo_base = self.__servicio.calcular_costo(self.__duracion)
        if len(args) == 0:
            return costo_base
        elif len(args) == 1:
            impuesto = args[0]
            if 0 <= impuesto <= 1:
                return costo_base * (1 + impuesto)
        elif len(args) == 2:
            impuesto, descuento = args
            if descuento >= 0 and descuento <= costo_base:
                return (costo_base * (1 + impuesto)) - descuento
        return -1.0

    # Registro de eventos
    def _registrar_evento(self, mensaje: str):
        try:
            with open("registro_exitosas.log", "a", encoding="utf-8") as f:
                f.write(f"[EVENTO] {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} | {mensaje}\n")
        except:
            print("⚠️ Error al guardar log")

    # Getters
    def get_codigo(self): return self.__codigo_reserva
    def get_estado(self): return self.__estado
    def get_cliente(self): return self.__cliente
    def get_servicio(self): return self.__servicio

    @classmethod
    def obtener_todas(cls):
        return cls._lista_reservas_exitosas

# ==============================================
# 🧪 PRUEBAS DE RESERVAS EXITOSAS
# ==============================================
if __name__ == "__main__":
    print("===== PRUEBAS: RESERVAS EXITOSAS =====")

    # Datos válidos
    c1 = Cliente(1, "María López", "1098765432", "maria@correo.com")
    c2 = Cliente(2, "Carlos Ruiz", "1011223344", "carlos@correo.com")

    s1 = ReservaSala(1, "Sala Principal", 50000, True)
    s2 = AlquilerEquipo(2, "Proyector 4K", 20000, True)

    try:
        # ✅ Reserva Exitosa 1
        print("\n→ Reserva 1:")
        r1 = ReservaExitosa(1, c1, s1, 3)
        r1.confirmar_reserva()
        print(f"Estado: {r1.get_estado()} | Código: {r1.get_codigo()}")
        print(f"Costo (15% impuesto): ${r1.calcular_total(0.15):,}")

        # ✅ Reserva Exitosa 2
        print("\n→ Reserva 2:")
        r2 = ReservaExitosa(2, c2, s2, 2)
        r2.confirmar_reserva()
        print(f"Estado: {r2.get_estado()} | Código: {r2.get_codigo()}")
        print(f"Costo (10% impuesto - $5.000 descuento): ${r2.calcular_total(0.10, 5000):,}")

        # ✅ Cancelación válida
        print("\n→ Cancelar Reserva 1:")
        r1.cancelar_reserva("Cambio de horario")
        print(f"Nuevo estado: {r1.get_estado()}")

    except Exception as e:
        print(f"❌ Inesperado: {e}")

    print(f"\nTotal exitosas: {len(ReservaExitosa.obtener_todas())}")
    print("=== FIN PRUEBAS EXITOSAS ===")
# Mensaje para el equipo: Aquí deben poner sus casos de uso