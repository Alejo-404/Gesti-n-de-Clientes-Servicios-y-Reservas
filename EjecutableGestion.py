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

# ✅ EXCEPCIONES (FUNDAMENTAL PARA LO FALLIDO)
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
# ❌ CLASE RESERVA - SOLO LÓGICA FALLIDA / ERRORES
# ==============================================
class ReservaFallida(Entidad):
    __cliente: Cliente
    __servicio: Servicio
    __duracion: int
    __estado: str
    __codigo_reserva: str
    _lista_reservas_fallidas = []

    def __init__(self, id: int, cliente: Cliente, servicio: Servicio, duracion: int):
        super().__init__(id)
        try:
            # ✅ AQUÍ SE EVALÚAN TODOS LOS ERRORES POSIBLES
            if not isinstance(cliente, Cliente):
                raise DatoInvalidoError("El objeto no es un Cliente válido")
            if not isinstance(servicio, Servicio):
                raise DatoInvalidoError("El objeto no es un Servicio válido")
            if duracion <= 0:
                raise ParametroFaltanteError(f"Duración inválida: {duracion} (debe ser > 0)")
            if not servicio.esta_disponible():
                raise ServicioNoDisponibleError(f"Servicio '{servicio.get_nombre()}' está ocupado/no disponible")

            # Si llega aquí, no debería ser fallida, pero forzamos error si hay inconsistencia
            costo_prueba = servicio.calcular_costo(duracion)
            if costo_prueba < 0:
                raise CalculoInconsistenteError("El sistema calculó un costo negativo")

            # Si pasa todo, igual marcamos como fallida para demostración
            raise ReservaInvalidaError("Reserva rechazada por regla interna del sistema")

        # ✅ MANEJO DE CADA ERROR ESPECÍFICO
        except (DatoInvalidoError, ParametroFaltanteError, ServicioNoDisponibleError) as e:
            self.__estado = "fallida"
            self.__codigo_reserva = f"RES-FALL-{id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            self._registrar_error(f"❌ RESERVA FALLIDA | Código: {self.__codigo_reserva} | MOTIVO: {str(e)}")
            ReservaFallida._lista_reservas_fallidas.append(self)
            # Encadenamiento de excepciones (requisito del ejercicio)
            raise ReservaInvalidaError("No se pudo procesar la solicitud") from e

        except CalculoInconsistenteError as e:
            self.__estado = "fallida"
            self.__codigo_reserva = f"RES-FALL-{id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            self._registrar_error(f"❌ RESERVA FALLIDA | Código: {self.__codigo_reserva} | MOTIVO: Cálculo inconsistente -> {str(e)}")
            ReservaFallida._lista_reservas_fallidas.append(self)
            raise

        except Exception as e:
            self.__estado = "fallida"
            self.__codigo_reserva = f"RES-FALL-{id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            self._registrar_error(f"❌ ERROR CRÍTICO | Código: {self.__codigo_reserva} | MOTIVO: Error inesperado -> {str(e)}")
            ReservaFallida._lista_reservas_fallidas.append(self)
            raise ErrorSistema("Fallo grave del sistema") from e

    # Métodos que NO deben funcionar (operaciones inválidas)
    def intentar_operacion(self):
        raise OperacionNoPermitidaError("Operación no válida para reservas fallidas")
