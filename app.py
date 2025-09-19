import os
import requests
import base64
import boto3
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import logging
from botocore.exceptions import BotoCoreError, ClientError

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# Configurar logging
logging.basicConfig(level=logging.INFO)

# Configuración para Render - manejar correctamente el puerto
port = int(os.environ.get('PORT', 5000))

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/speak', methods=['POST'])
def speak_text():
    try:
        data = request.json
        text = data.get('text', '')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        # Modo emergencia: usar navegador siempre
        app.logger.warning("Modo emergencia activado - usando navegador TTS")
        return jsonify({
            'audioContent': None,
            'audioUrl': None,
            'useBrowserTTS': True,
            'text': text
        })
            
    except Exception as e:
        app.logger.error(f"Exception in speak_text: {str(e)}")
        return jsonify({
            'audioContent': None,
            'audioUrl': None,
            'useBrowserTTS': True,
            'text': text,
            'error': str(e)
        }), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        message = data.get('message', '')
        
        if not message:
            return jsonify({'error': 'No message provided'}), 400
        
        # Respuestas inteligentes basadas en palabras clave
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['hola', 'buenos días', 'buenas tardes', 'saludos']):
            response = "¡Hola! Un gusto saludarte. Somos la Fundación VANALI. Nuestro objetivo social es apoyar el emprendimiento de las mujeres cabeza de familia a través de cursos de manualidades."
        elif any(word in message_lower for word in ['curso', 'cursos', 'ofrecen', 'qué hacen', 'muñeco', 'noel']):
            response = "Actualmente estamos dictando dos cursos muy especiales y navideños:\n1. Curso de Muñeco Papá Noel.\n2. Curso de Muñeco Mamá Noel."
        elif any(word in message_lower for word in ['dónde', 'donde', 'ubicación', 'ubicacion', 'ubicada', 'lugar', 'dirección', 'direccion', 'dirigirme', 'local', 'sitio', 'fusagasugá', 'fusagasuga', 'barrio', 'gaitán', 'gaitan', 'colegio', 'manuel', 'humberto', 'conjunto', 'andalucía', 'andaluci', 'andalucia']):
            response = "Los cursos son presenciales en la ciudad de Fusagasugá. Las clases se dictan en el Conjunto Andalucía, ubicado en el barrio Gaitán, específicamente frente al Colegio Manuel Humberto. ¡Es muy fácil de encontrar!"
        elif any(word in message_lower for word in ['profesor', 'profesora', 'quién enseña', 'imparte', 'rocío']):
            response = "Nuestros cursos son impartidos por la profesora Rocío, una experta en creación de muñecos y manualidades con más de 20 años de experiencia. ¡Aprenderás muchísimo con ella!"
        elif any(word in message_lower for word in ['inscribir', 'inscripción', 'requisitos', 'cómo me inscribo']):
            response = "Lo primero es realizar tu inscripción a través de nuestros canales de servicio oficiales. Con gusto te puedo proporcionar los contactos para que completes tu proceso."
        elif any(word in message_lower for word in ['materiales', 'incluidos', 'comprar', 'llevar']):
            response = "Para que te centres solo en aprender, el valor del curso incluye todos los materiales necesarios para elaborar tus muñecos. Sin embargo, si lo prefieres, también puedes adquirirlos por tu cuenta."
        elif any(word in message_lower for word in ['dura', 'duración', 'horas', 'clases', 'semanas']):
            response = "La duración es la siguiente:\n- Curso de Papá Noel: 4 clases de 2 horas cada una.\n- Curso de Mamá Noel: 5 clases de 2 horas cada una.\nAmbos se pueden tomar los días martes y jueves."
        elif any(word in message_lower for word in ['horario', 'horarios', 'cuándo', 'cuando', 'días', 'dias', 'tarde', 'mañana', 'manana', 'noche', 'hora', 'horas', 'inicio', 'comienza', 'empieza', 'termina', 'finaliza', 'duración', 'duracion', 'lunes', 'martes', 'miércoles', 'miercoles', 'jueves', 'viernes', 'sábado', 'sabado', 'domingo', 'fin de semana', 'weekend', 'turno', 'jornada', 'disponibilidad', 'disponible']):
            response = "Tenemos dos horarios disponibles para tu comodidad:\n1. Horario de la mañana: de 9:00 a. m. a 11:00 a. m., de lunes a viernes.\n2. Horario de la tarde: de 3:00 p. m. a 5:00 p. m., de lunes a viernes."
        elif any(word in message_lower for word in ['certificado', 'premio', 'recibo', 'finalizar', 'ganador']):
            response = "¡Por supuesto! Al finalizar, recibirás un certificado que acredita el curso recibido. Además, ¡hay un premio especial si tu muñeco es calificado como el ganador del curso!"
        elif any(word in message_lower for word in ['precio', 'costo', 'valor', 'cuánto cuesta', 'tarifa']):
            response = "Para conocer los precios actualizados y toda la información sobre costos, te recomiendo contactar directamente a nuestra instructora Rocío por WhatsApp. Ella te dará todos los detalles personalizados. Da click en el icono de whatsapp, el sistema te comunicará automáticamente con ella"
        
        # NUEVAS PREGUNTAS SOBRE FECHAS
        elif any(word in message_lower for word in ['fecha', 'fechas', 'cuándo empieza', 'cuando inician los cursos', 'cuándo comienza', 'cuando comienzan', 'inicio del curso', 'cuando inicia el curso', 'próximo curso', 'proximo curso', 'cuando inicia', 'cuando inician', 'día de inicio', 'dia de inicio', 'empezar', 'comenzar', 'iniciar', 'arranque', 'cuándo arranca', 'cuando arranca']):
            response = "Para saber qué fecha es la más próxima contáctate vía WhatsApp"
        elif any(word in message_lower for word in ['me dices cuando comienzan', 'dime cuando comienzan', 'cuando comienzan', 'cuándo comienzan', 'me dices cuando empiezan', 'dime cuando empiezan', 'cuando empiezan', 'cuándo empiezan', 'me dices la fecha', 'dime la fecha', 'quiero saber la fecha', 'necesito saber la fecha', 'información de fechas', 'informacion de fechas', 'fechas de inicio', 'cuando son las clases', 'cuándo son las clases']):
            response = "Para saber qué fecha es la más próxima contáctate vía WhatsApp, por favor"
        
        elif any(word in message_lower for word in ['gracias', 'muchas gracias', 'mil gracias', 'gracias rocio', 'gracias rocio', 'agradecer', 'agradecido', 'agradecida', 'amable', 'thanks', 'thank you', 'merci', 'te lo agradezco', 'se lo agradezco', 'appreciate', 'agradecimiento', 'valoro', 'agradecimiento', 'excelente ayuda', 'buena ayuda', 'muy amable', 'que amable', 'eres muy amable', 'muy agradecido', 'muy agradecida', 'perfecto', 'genial', 'fantástico', 'fantastico', 'estupendo', 'increíble', 'increible', 'brutal', 'chévere', 'chevere', 'cool', 'ok', 'okay', 'vale', 'listo', 'de acuerdo', 'entendido', 'comprendido', 'excelente', 'bien', 'good', 'nice', 'awesome', 'great']):
            response = "¡Es un placer ayudarte! Estoy aquí para lo que necesites. ¿Hay algo más en lo que pueda asistirte?"
        else:
            responses = [
                "Entiendo tu consulta sobre nuestros cursos. Te recomiendo contactar directamente a nuestra instructora Rocío por WhatsApp. Ella te dará todos los detalles personalizados. Da click en el icono de whatsapp, el sistema te comunicará automáticamente con ella.",
                "Gracias por tu mensaje. Para información más específica y personalizada, te sugiero comunicarte con nuestra instructora Rocío por WhatsApp. Da click en el icono de whatsapp y el sistema te conectará directamente con ella.",
                "Comprendo tu pregunta sobre la Fundación VANALI. Para una atención más detallada, te recomiendo contactar a Rocío por WhatsApp. Solo da click en el icono de whatsapp y serás atendido personalmente.",
                "Excelente pregunta sobre nuestros cursos. Para brindarte la mejor atención personalizada, te sugerimos contactar a nuestra instructora Rocío por WhatsApp. Da click en el icono de whatsapp y el sistema te comunicará automáticamente con ella.",
                "Tomo nota de tu consulta. Para resolver tus dudas de manera más específica, te recomendamos contactar directamente con Rocío por WhatsApp. Da click en el icono de whatsapp y serás atendido personalmente."
            ]
            response = responses[len(message) % len(responses)]
        
        return jsonify({'response': response})
            
    except Exception as e:
        app.logger.error(f"Exception in chat: {str(e)}")
        return jsonify({
            'response': "Estoy teniendo dificultades técnicas. Por favor contacta directamente a Rocío por WhatsApp para más información."
        })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Endpoint para verificar el estado del servicio"""
    return jsonify({
        'status': 'healthy',
        'aws_configured': False,
        'service': 'Modo emergencia - Navegador TTS'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port, debug=False)
