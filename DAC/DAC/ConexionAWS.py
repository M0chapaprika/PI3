import pyodbc

def test_sqlserver_connection():
    """
    Prueba la conexión a la BD 'Alcolimetro' en el servidor IANDAVID\SQLSERVER
    usando autenticación de Windows y contraseña.
    """

    connection_string = (
        "DRIVER={SQL Server};"
        "SERVER=IANDAVID\\SQLSERVER;"
        "DATABASE=Alcolimetro;"
        "Trusted_Connection=yes;"
        "PWD=SoyBienM0cha1;"
    )

    try:
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()

        # Verificar versión del servidor
        cursor.execute("SELECT @@VERSION AS version")
        version = cursor.fetchone()[0]

        # Listar bases de datos disponibles
        cursor.execute("SELECT name FROM sys.databases")
        databases = [db[0] for db in cursor.fetchall()]

        print("\n✅ ¡Conexión exitosa a SQL Server local!")
        print(f"• Versión SQL Server: {version}")
        print("\n📊 Bases de datos disponibles:")
        for i, db in enumerate(databases, 1):
            print(f"  {i}. {db}")

        conn.close()
        return True

    except pyodbc.Error as ex:
        print("\n❌ Error de conexión:")
        print(f"Código: {ex.args[0]}")
        print(f"Mensaje: {ex.args[1]}")
        return False


# Probar conexión
test_sqlserver_connection()
