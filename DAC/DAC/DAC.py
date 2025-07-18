from flask import Flask, render_template, request, redirect, url_for, jsonify
import pyodbc
from datetime import datetime

app = Flask(__name__)


def get_db_connection():
    return pyodbc.connect(
        'DRIVER={SQL Server};'
        'SERVER=IANDAVID\SQLSERVER;'
        'DATABASE=Alcolimetro;'
        'Trusted_Connection=yes;'
        'PWD=SoyBienM0cha1;'
    )
    
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/datos', methods=['POST'])
def recibir_datos():
    """Endpoint para recibir datos del sensor Arduino"""
    try:
        # Obtener datos del formulario
        sensor_id = request.form.get('sensor_id', '1')
        valor_sensor = request.form.get('valor')
        concentracion = request.form.get('concentracion')
        
        # Validar datos requeridos
        if not valor_sensor or not concentracion:
            return jsonify({"status": "error", "message": "Datos incompletos"}), 400
        
        # Convertir a tipos adecuados
        valor_sensor = int(valor_sensor)
        concentracion = float(concentracion)
        fecha_actual = datetime.now()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener el primer personal autorizado (asociado al sensor)
        cursor.execute("SELECT TOP 1 idAutorizado FROM Autorizados")
        id_autorizado = cursor.fetchone()[0]
        
        # Obtener ID de persona asociada al sensor (por ahora fijo)
        id_persona = 10  # Esto debería asociarse dinámicamente en el futuro
        
        # Insertar registro en la base de datos
        cursor.execute("""
            INSERT INTO Registros (Fecha, idPersona, idAutorizado, Medicion, ValorSensor)
            VALUES (?, ?, ?, ?, ?)
        """, (fecha_actual, id_persona, id_autorizado, concentracion, valor_sensor))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "status": "success", 
            "message": "Datos almacenados",
            "sensor_id": sensor_id,
            "valor_sensor": valor_sensor,
            "concentracion": concentracion
        }), 200
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ... (las demás rutas se mantienen igual) ...

@app.route('/buscar')
def buscar():
    query = request.args.get('query', '')
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT E.Matricula AS id, 
               P.Nombre + ' ' + P.APaterno + ' ' + P.AMaterno AS nombre, 
               C.Carrera AS carrera
        FROM Estudiantes E
        JOIN Personas P ON E.idPersona = P.idPersona
        JOIN AsignacionTutores AT ON E.idAsignacion = AT.idAsignacion
        JOIN Grupos G ON AT.idGrupo = G.idGrupo
        JOIN Carreras C ON G.idCarrera = C.idCarrera
        WHERE E.Matricula LIKE ? OR P.Nombre LIKE ? OR P.APaterno LIKE ? OR P.AMaterno LIKE ?
    """, (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%'))
    
    results = []
    for row in cursor.fetchall():
        results.append({
            'id': row.id,
            'nombre': row.nombre,
            'carrera': row.carrera
        })
    
    conn.close()
    return jsonify(results)

@app.route('/datospersonales')
def datospersonales():
    matricula = request.args.get('matricula')
    if not matricula:
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT E.Matricula, 
               P.Nombre + ' ' + P.APaterno + ' ' + P.AMaterno AS NombreCompleto,
               P.Edad, 
               'Calle ' + CAST(P.idPersona AS VARCHAR) + ', Col. Centro' AS Domicilio,
               C.Carrera
        FROM Estudiantes E
        JOIN Personas P ON E.idPersona = P.idPersona
        JOIN AsignacionTutores AT ON E.idAsignacion = AT.idAsignacion
        JOIN Grupos G ON AT.idGrupo = G.idGrupo
        JOIN Carreras C ON G.idCarrera = C.idCarrera
        WHERE E.Matricula = ?
    """, (matricula,))
    
    estudiante = cursor.fetchone()
    conn.close()
    
    if estudiante:
        estudiante_data = {
            'id': estudiante.Matricula,
            'nombre': estudiante.NombreCompleto,
            'edad': estudiante.Edad,
            'domicilio': estudiante.Domicilio,
            'carrera': estudiante.Carrera
        }
        return render_template('datospersonales.html', estudiante=estudiante_data)
    else:
        return redirect(url_for('index'))

@app.route('/registro')
def registro():
    matricula = request.args.get('matricula')
    if not matricula:
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Obtener datos del estudiante
    cursor.execute("""
        SELECT E.Matricula, 
               P.Nombre + ' ' + P.APaterno + ' ' + P.AMaterno AS NombreCompleto,
               P.Edad, 
               'Calle ' + CAST(P.idPersona AS VARCHAR) + ', Col. Centro' AS Domicilio,
               C.Carrera
        FROM Estudiantes E
        JOIN Personas P ON E.idPersona = P.idPersona
        JOIN AsignacionTutores AT ON E.idAsignacion = AT.idAsignacion
        JOIN Grupos G ON AT.idGrupo = G.idGrupo
        JOIN Carreras C ON G.idCarrera = C.idCarrera
        WHERE E.Matricula = ?
    """, (matricula,))
    estudiante = cursor.fetchone()
    
    # Obtener registros de alcohol
    cursor.execute("""
        SELECT CONVERT(VARCHAR(10), R.Fecha, 120) AS Fecha, 
               CONVERT(VARCHAR(5), R.Fecha, 108) AS Hora, 
               Per.Nombre + ' ' + Per.APaterno AS Personal,
               R.Medicion AS Nivel,
               CASE 
                   WHEN R.Medicion > 0.8 THEN 'Nivel peligroso'
                   WHEN R.Medicion > 0.5 THEN 'Nivel alto'
                   ELSE 'Normal'
               END AS Comentario
        FROM Registros R
        JOIN Autorizados A ON R.idAutorizado = A.idAutorizado
        JOIN Personas Per ON A.idPersona = Per.idPersona
        WHERE R.idPersona = (SELECT idPersona FROM Estudiantes WHERE Matricula = ?)
        ORDER BY R.Fecha DESC
    """, (matricula,))
    
    registros = []
    for row in cursor.fetchall():
        registros.append({
            'fecha': row.Fecha,
            'hora': row.Hora,
            'personal': row.Personal,
            'nivel': row.Nivel,
            'comentario': row.Comentario
        })
    
    conn.close()
    
    if estudiante:
        estudiante_data = {
            'id': estudiante.Matricula,
            'nombre': estudiante.NombreCompleto,
            'edad': estudiante.Edad,
            'domicilio': estudiante.Domicilio,
            'carrera': estudiante.Carrera
        }
        return render_template('registro.html', estudiante=estudiante_data, registros=registros)
    else:
        return redirect(url_for('index'))

@app.route('/registroalcohol')
def registro_alcohol():
    matricula = request.args.get('matricula')
    if not matricula:
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Obtener datos del estudiante
    cursor.execute("""
        SELECT E.Matricula, 
               P.Nombre + ' ' + P.APaterno + ' ' + P.AMaterno AS NombreCompleto,
               P.Edad, 
               'Calle ' + CAST(P.idPersona AS VARCHAR) + ', Col. Centro' AS Domicilio,
               C.Carrera
        FROM Estudiantes E
        JOIN Personas P ON E.idPersona = P.idPersona
        JOIN AsignacionTutores AT ON E.idAsignacion = AT.idAsignacion
        JOIN Grupos G ON AT.idGrupo = G.idGrupo
        JOIN Carreras C ON G.idCarrera = C.idCarrera
        WHERE E.Matricula = ?
    """, (matricula,))
    estudiante = cursor.fetchone()
    
    # Obtener operadores autorizados
    cursor.execute("""
        SELECT A.idAutorizado AS id, 
               Per.Nombre + ' ' + Per.APaterno AS nombre
        FROM Autorizados A
        JOIN Personas Per ON A.idPersona = Per.idPersona
    """)
    operadores = cursor.fetchall()
    
    conn.close()
    
    if estudiante:
        estudiante_data = {
            'id': estudiante.Matricula,
            'nombre': estudiante.NombreCompleto,
            'edad': estudiante.Edad,
            'domicilio': estudiante.Domicilio,
            'carrera': estudiante.Carrera
        }
        niveles = [round(i * 0.05, 2) for i in range(0, 41)]
        # Convertir operadores a lista de diccionarios
        operadores_list = [{'id': row.id, 'nombre': row.nombre} for row in operadores]
        return render_template('registroalcohol.html', 
                              estudiante=estudiante_data, 
                              niveles=niveles, 
                              operadores=operadores_list)
    else:
        return redirect(url_for('index'))

@app.route('/registraralcohol', methods=['POST'])
def registrar_alcohol():
    matricula = request.form['matricula']
    fecha = request.form['fecha']
    hora = request.form['hora']
    id_operador = request.form['id_operador']  # Cambiamos personal por id_operador
    nivel = request.form['nivel']
    comentario = request.form['comentario']
    
    # Combinar fecha y hora en un objeto datetime
    fecha_hora = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Obtener idPersona del estudiante
        cursor.execute("SELECT idPersona FROM Estudiantes WHERE Matricula = ?", (matricula,))
        id_persona = cursor.fetchone()[0]
        
        # Insertar en la tabla Registros usando el id del operador
        cursor.execute("""
            INSERT INTO Registros (Fecha, idPersona, idAutorizado, Medicion)
            VALUES (?, ?, ?, ?)
        """, (fecha_hora, id_persona, id_operador, nivel))
        
        conn.commit()
        return redirect(url_for('registro', matricula=matricula))
    except Exception as e:
        conn.rollback()
        return f"Error: {str(e)}", 500
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)