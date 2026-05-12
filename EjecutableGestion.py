#Cancelacion de Reservas.

def cancelar_reserva(self, motivo: str = "No especificado") -> bool:
    try:
        # 1. Validar si la reserva ya está en un estado que no permite cancelación
        if self.__estado == "cancelada":
            raise OperacionNoPermitidaError(f"La reserva {self.__codigo_reserva} ya se encuentra cancelada.")
        
        if self.__estado == "finalizada":
            raise OperacionNoPermitidaError("No se puede cancelar una reserva que ya ha sido completada.")

        # 2. Cambiar el estado de la reserva
        self.__estado = "cancelada"

        # 3. Liberar el servicio para que otros puedan usarlo
        self.__servicio.set_disponibilidad(True)

        # 4. Registrar el evento (usando el log de Luisa)
        self.registrar_evento(f"CANCELACIÓN REALIZADA | Código: {self._codigo_reserva} | Motivo: {motivo}")
        
        print(f"Reserva {self.__codigo_reserva} cancelada exitosamente.")
        return True

    except OperacionNoPermitidaError as e:
        self._registrar_evento(f"INTENTO FALLIDO DE CANCELACIÓN | Motivo: {str(e)}")
        print(f"Error al cancelar: {e}")
        return False