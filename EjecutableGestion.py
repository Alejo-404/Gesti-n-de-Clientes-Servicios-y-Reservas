# =========================================
# OPERACIÓN 04 - CREACIÓN SERVICIO INVÁLIDO
# =========================================

class ReservaSala:
    def __init__(self, horas):

        if horas <= 0:
            raise ValueError("Horas inválidas")

        self.horas = horas

    def calcular_costo(self):
        return self.horas * 50


# ==========================
# SERVICIO INVÁLIDO
# ==========================

try:

    servicio_invalido = ReservaSala(-5)

    print("Servicio creado correctamente")

except Exception as e:

    print("Error servicio inválido:", e)