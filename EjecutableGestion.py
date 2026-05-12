# Mensaje para el equipo: Aquí deben poner sus casos de uso
class Customer:

    def __init__(self, name, email):

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


# INVALID CUSTOMER

try:

    customer2 = Customer(
        "",
        "wrongemail"
    )

    print(customer2.show_info())

except Exception as e:

    print("\nInvalid Customer Detected")
    print(f"Error: {e}")
    