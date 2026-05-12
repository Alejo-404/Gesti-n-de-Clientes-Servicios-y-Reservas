# Mensaje para el equipo: Aquí deben poner sus casos de uso
def _init_(self, name, email):

        if not name.strip():

            raise ValueError(
                "Name cannot be empty"
            )

        if "@" not in email:

            raise ValueError(
                "Invalid email format"
            )

        self.name = name
        self.email = email

def show_info(self):

        return (
            f"Customer: {self.name} | "
            f"Email: {self.email}"
        )
        