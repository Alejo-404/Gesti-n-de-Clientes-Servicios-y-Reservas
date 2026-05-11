# Mensaje para el equipo: Aquí deben poner sus caso
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


print("\nCUSTOMER SYSTEM\n")


# VALID CUSTOMER
try:

    customer1 = Customer(
        "Camila",
        "camila@gmail.com"
    )

    print("\nValid Customer Created")
    print(customer1.show_info())

except Exception as e:

    print(f"Error: {e}")


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
    
        