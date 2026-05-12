#Calculo detallado de costos para la reserva, incluyendo impuestos y descuentos.
def calcular_costo_detallado(self, tasa_impuesto: float = 0.0, monto_descuento: float = 0.0) -> dict:
    try:
        # Obtener el costo base desde la lógica de Miguel/Jorge
        costo_base = self.__servicio.calcular_costo(self.__duracion)
        
        if costo_base < 0:
            raise CalculoInconsistenteError("El costo base no puede ser negativo.")

        # Aplicar cálculos
        valor_impuesto = costo_base * tasa_impuesto
        total = (costo_base + valor_impuesto) - monto_descuento

        # Retornar un diccionario con el desglose (muy útil para facturación)
        return {
            "base": costo_base,
            "impuesto": valor_impuesto,
            "descuento": monto_descuento,
            "total": max(0, total) # Evita totales negativos
        }

    except Exception as e:
        self._registrar_evento(f"ERROR EN CÁLCULO | {str(e)}")
        raise CalculoInconsistenteError(f"Error al procesar costos: {e}")