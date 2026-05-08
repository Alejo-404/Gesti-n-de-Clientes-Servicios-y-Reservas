# =========================================
# OPERACIÓN 04 - CREACIÓN SERVICIO INVÁLIDO
# =========================================

class Servicio:

    def __init__(self, nombre, horas):

        if horas <= 0:
            raise ValueError("Horas inválidas")

        self.nombre = nombre
        self.horas = horas

    def calcular_costo(self):

        return self.horas * 50


# ==========================
# SERVICIO INVÁLIDO
# ==========================

try:

    servicio_invalido = Servicio("Reserva Sala", -5)

    print("Servicio creado correctamente")

except Exception as e:

    print("Error servicio inválido:", e)