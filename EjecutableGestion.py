# =========================================
# OPERACIÓN 03 - CREACIÓN SERVICIO VÁLIDO
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
# SERVICIO VÁLIDO
# ==========================

try:

    servicio_valido = Servicio("Reserva Sala", 2)

    print("Servicio válido creado correctamente")
    print("Servicio:", servicio_valido.nombre)
    print("Costo:", servicio_valido.calcular_costo())

except Exception as e:

    print("Error:", e)