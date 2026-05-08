# =========================================
# OPERACIÓN 03 - CREACIÓN SERVICIO VÁLIDO
# =========================================

class ReservaSala:
    def __init__(self, horas):

        if horas <= 0:
            raise ValueError("Horas inválidas")

        self.horas = horas

    def calcular_costo(self):
        return self.horas * 50


# ==========================
# SERVICIO VÁLIDO
# ==========================

try:
    servicio_valido = ReservaSala(2)

    print("Servicio válido creado correctamente")
    print("Costo:", servicio_valido.calcular_costo())

except Exception as e:
    print("Error:", e)


# ==========================
# SERVICIO INVÁLIDO
# ==========================

try:
    servicio_invalido = ReservaSala(-1)

except Exception as e:
    print("Error servicio inválido:", e)