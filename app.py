import os
import requests
import base64
import boto3
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import logging
from botocore.exceptions import BotoCoreError, ClientError
import re

app = Flask(__name__)
CORS(app)

# Configurar logging
logging.basicConfig(level=logging.INFO)

# Configuración AWS Polly
AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_KEY")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# DEBUG: Verificar configuración AWS
@app.before_request
def log_aws_config():
    app.logger.info(f"AWS_ACCESS_KEY configured: {bool(AWS_ACCESS_KEY)}")
    app.logger.info(f"AWS_SECRET_KEY configured: {bool(AWS_SECRET_KEY)}")
    app.logger.info(f"AWS_REGION: {AWS_REGION}")

def improve_pronunciation(text):
    """Mejora la pronunciación de texto legal con énfasis en palabras clave"""
    # Palabras legales que necesitan mejor pronunciación
    improvements = {
        'abogada': 'abogáda',
        'legal': 'legál',
        'cliente': 'clienté',
        'proceso': 'procéso',
        'judicial': 'judiciál',
        'documento': 'documentó',
        'contrato': 'contráto',
        'custodia': 'custódia',
        'pensión': 'pensión',
        'alimentaria': 'alimentária',
        'herencia': 'heréncia',
        'testamento': 'testaménto',
        'demanda': 'demánda',
        'juzgado': 'juzgádo',
    }
    
    for word, replacement in improvements.items():
        text = text.replace(word, f"<emphasis level=\"moderate\">{word}</emphasis>")
    
    return text

def add_natural_pauses(text):
    """Añade pausas naturales en el texto para mejor fluidez"""
    # Pausas después de signos de puntuación
    text = re.sub(r'([.!?])', r'\1<break time="500ms"/>', text)
    
    # Pausas menores después de comas
    text = re.sub(r'(,)', r'\1<break time="200ms"/>', text)
    
    # Pausas en enumeraciones
    text = re.sub(r'(:)', r'\1<break time="300ms"/>', text)
    
    return text

def create_ssml_text(text):
    """Crea texto SSML optimizado para voz natural"""
    # Mejorar pronunciación
    improved_text = improve_pronunciation(text)
    
    # Añadir pausas naturales
    text_with_pauses = add_natural_pauses(improved_text)
    
    # Crear SSML con configuración optimizada
    ssml = f"""
    <speak>
        <prosody rate="105%" pitch="+2%" volume="loud">
            <amazon:effect name="drc">
                <amazon:effect vocal-tract-length="+3%">
                    {text_with_pauses}
                </amazon:effect>
            </amazon:effect>
        </prosody>
    </speak>
    """
    
    return ssml.strip()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/speak', methods=['POST'])
def speak_text():
    try:
        data = request.json
        text = data.get('text', '')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        # Verificación DIRECTA de credenciales
        if not AWS_ACCESS_KEY or not AWS_SECRET_KEY:
            app.logger.error("AWS credentials not configured - usando modo navegador")
            return jsonify({
                'audioContent': None,
                'audioUrl': None,
                'useBrowserTTS': True,
                'text': text
            })
        
        # Configurar cliente de Polly
        app.logger.info("Configurando cliente Polly...")
        polly = boto3.client('polly',
                            aws_access_key_id=AWS_ACCESS_KEY,
                            aws_secret_access_key=AWS_SECRET_KEY,
                            region_name=AWS_REGION)
        
        # Crear SSML optimizado
        ssml_text = create_ssml_text(text)
        app.logger.info(f"SSML creado para texto: {text[:50]}...")
        
        # Sintetizar voz con Polly - motor neuronal para voz más natural
        app.logger.info("Sintetizando con motor neuronal...")
        response = polly.synthesize_speech(
            Text=ssml_text,
            TextType='ssml',  # Usar SSML
            OutputFormat='mp3',
            VoiceId='Lupe',
            Engine='neural',  # Motor neuronal para voz más natural
            LanguageCode='es-US'
        )
        
        app.logger.info("Audio sintetizado correctamente con motor neuronal")
        
        # Convertir audio a base64
        audio_data = response['AudioStream'].read()
        audio_content = base64.b64encode(audio_data).decode('utf-8')
        
        return jsonify({
            'audioContent': audio_content,
            'audioUrl': f"data:audio/mp3;base64,{audio_content}",
            'useBrowserTTS': False,
            'engine': 'neural'
        })
            
    except (BotoCoreError, ClientError) as error:
        app.logger.error(f"AWS Polly error: {error}")
        
        # Fallback a voz estándar si falla neural
        try:
            if 'polly' not in locals():
                polly = boto3.client('polly',
                                    aws_access_key_id=AWS_ACCESS_KEY,
                                    aws_secret_access_key=AWS_SECRET_KEY,
                                    region_name=AWS_REGION)
            
            app.logger.info("Intentando con motor estándar como fallback...")
            response = polly.synthesize_speech(
                Text=text,
                OutputFormat='mp3',
                VoiceId='Lupe'
            )
            
            audio_data = response['AudioStream'].read()
            audio_content = base64.b64encode(audio_data).decode('utf-8')
            
            return jsonify({
                'audioContent': audio_content,
                'audioUrl': f"data:audio/mp3;base64,{audio_content}",
                'useBrowserTTS': False,
                'engine': 'standard'
            })
            
        except Exception as fallback_error:
            app.logger.error(f"Fallback también falló: {fallback_error}")
            return jsonify({
                'audioContent': None,
                'audioUrl': None,
                'useBrowserTTS': True,
                'text': text,
                'error': str(error)
            })
            
    except Exception as e:
        app.logger.error(f"Exception in speak_text: {str(e)}")
        return jsonify({
            'audioContent': None,
            'audioUrl': None,
            'useBrowserTTS': True,
            'text': text,
            'error': str(e)
        })

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        message = data.get('message', '')
        
        if not message:
            return jsonify({'error': 'No message provided'}), 400
        
        # Respuestas inteligentes basadas en consultas legales
        message_lower = message.lower()
        
        # Solicitudes de repetición
        if any(word in message_lower for word in ['repetir', 'repita', 'otra vez', 'no entendí', 'no entendi', 'puede repetir', 'otra vez por favor']):
            response = "Claro, con gusto repito la información. ¿Le gustaría que repita las opciones de rol, las categorías de caso, los horarios disponibles, o hay algo específico que no quedó claro?"
        
        # Repetición de opciones de rol
        elif any(word in message_lower for word in ['rol', 'opciones de rol', 'víctima o demandante', 'victima o demandante', 'qué rol', 'que rol']):
            response = """Para continuar, necesito saber cuál es su situación:

Víctima: si ha sufrido un daño o perjuicio y necesita apoyo legal para defender sus derechos.

Demandante: si está iniciando una acción legal contra otra persona o entidad.

Por favor dígame: ¿se considera víctima o demandante?"""
        
        # Repetición de categorías de caso
        elif any(word in message_lower for word in ['categorías', 'categorias', 'tipos de caso', 'qué categoría', 'que categoria', 'civil laboral penal']):
            response = """Las categorías de caso disponibles son:

Civil: para disputas entre familiares, propiedad o contratos.

Laboral: para temas de empleo, derechos laborales o conflictos con empleador.

Penal: para infracciones de ley, cargos criminales o detenciones.

Otros: si su caso no encaja en las categorías anteriores.

¿En cuál de estas categorías considera que está su caso?"""
        
        # Repetición de horarios
        elif any(word in message_lower for word in ['horarios', 'fechas', 'disponibilidad', 'qué horarios', 'que horarios', 'cuándo hay citas', 'cuando hay citas']):
            response = """Estas son nuestras disponibilidades para agendar su cita:

Lunes 29 de Septiembre: nueve quince de la mañana, diez treinta de la mañana, dos quince de la tarde, o tres treinta de la tarde.

Miércoles 1 de Octubre: ocho cuarenta y cinco de la mañana, once de la mañana, dos de la tarde, o cuatro quince de la tarde.

Viernes 3 de Octubre: nueve treinta de la mañana, diez cuarenta y cinco de la mañana, una treinta de la tarde, o tres cuarenta y cinco de la tarde.

¿Cuál de estos horarios le parece mejor?"""
        
        # Saludos y presentación
        elif any(word in message_lower for word in ['hola', 'buenos días', 'buenas tardes', 'saludos', 'buenos', 'buenas', 'iniciar', 'empezar']):
            response = """¡Bienvenido a TusAbogados.com! Estamos aquí para ofrecerle Asistencia Legal de forma inmediata.

Para comenzar, necesito saber cuál es su rol en este caso. ¿Se considera víctima o demandante?

Si necesita que repita las opciones, simplemente dígame 'repetir'."""
       
        # Confirmación de rol: Víctima
        elif any(word in message_lower for word in ['víctima', 'victima', 'soy víctima', 'soy victima']):
            response = """Entendido, ha seleccionado el rol de Víctima. Ahora necesito saber la categoría de su caso.

Las opciones son: civil, laboral, penal u otros.

¿Puede decirme en qué categoría cree que está su caso?"""
        
        # Confirmación de rol: Demandante
        elif any(word in message_lower for word in ['demandante', 'soy demandante']):
            response = """Entendido, ha seleccionado el rol de Demandante. Ahora necesito saber la categoría de su caso.

Las opciones son: civil, laboral, penal u otros.

¿Puede decirme en qué categoría cree que está su caso?"""
        
        # Categorías del caso después de seleccionar rol
        elif any(word in message_lower for word in ['civil']):
            response = "He registrado su caso en la categoría Civil. Para poder ayudarle mejor, ¿podría describirme brevemente su situación? Cuénteme qué está sucediendo."
        
        elif any(word in message_lower for word in ['laboral']):
            response = "He registrado su caso en la categoría Laboral. Para poder ayudarle mejor, ¿podría describirme brevemente su situación laboral? Cuénteme qué está ocurriendo."
        
        elif any(word in message_lower for word in ['penal']):
            response = "He registrado su caso en la categoría Penal. Para poder ayudarle mejor, ¿podría describirme brevemente su situación? Cuénteme los hechos."
        
        elif any(word in message_lower for word in ['otros', 'otro']):
            response = "He registrado su caso en la categoría Otros. Para poder ayudarle mejor, ¿podría describirme brevemente su situación? Cuénteme qué tipo de problema legal está enfrentando."
        
        # Respuesta cuando el usuario describe su caso
        elif len(message.strip()) > 25 and not any(word in message_lower for word in ['repetir', 'hola', 'si', 'no', 'quizás', 'quizas']):
            response = """Gracias por compartir los detalles de su caso. 

Le informo sobre nuestros honorarios: si el monto de su caso supera los diez millones de pesos, el proceso no tendrá costo inicial. Solo si recuperamos su dinero, cancelará un 10% del valor recuperado.

Ahora podemos agendar su cita. Tenemos disponibles:

Lunes 29 de Septiembre: mañana o tarde
Miércoles 1 de Octubre: mañana o tarde  
Viernes 3 de Octubre: mañana o tarde

¿Le gustaría que le detalle los horarios específicos o prefiere algún día en particular?"""
        
        # Solicitud de horarios específicos
        elif any(word in message_lower for word in ['horarios específicos', 'horarios especificos', 'qué horarios hay', 'que horarios hay', 'dígame los horarios', 'digame los horarios']):
            response = """Estos son los horarios disponibles:

Lunes 29 de Septiembre: 
- Mañana: nueve quince o diez treinta
- Tarde: dos quince o tres treinta

Miércoles 1 de Octubre:
- Mañana: ocho cuarenta y cinco o once
- Tarde: dos o cuatro quince

Viernes 3 de Octubre:
- Mañana: nueve treinta o diez cuarenta y cinco
- Tarde: una treinta o tres cuarenta y cinco

¿Cuál de estos horarios le conviene más?"""
        
        # Confirmación de cita por día
        elif any(word in message_lower for word in ['lunes', 'lunes 29']):
            response = "Para el Lunes 29 de Septiembre tenemos: nueve quince de la mañana, diez treinta de la mañana, dos quince de la tarde, o tres treinta de la tarde. ¿Cuál prefiere?"
        
        elif any(word in message_lower for word in ['miércoles', 'miercoles', 'miércoles 1', 'miercoles 1']):
            response = "Para el Miércoles 1 de Octubre tenemos: ocho cuarenta y cinco de la mañana, once de la mañana, dos de la tarde, o cuatro quince de la tarde. ¿Cuál prefiere?"
        
        elif any(word in message_lower for word in ['viernes', 'viernes 3']):
            response = "Para el Viernes 3 de Octubre tenemos: nueve treinta de la mañana, diez cuarenta y cinco de la mañana, una treinta de la tarde, o tres cuarenta y cinco de la tarde. ¿Cuál prefiere?"
        
        # Confirmación de cita por turno
        elif any(word in message_lower for word in ['mañana', 'manana', 'en la mañana']):
            response = "Tenemos horarios de mañana estos días: Lunes a las nueve quince o diez treinta, Miércoles a las ocho cuarenta y cinco u once, Viernes a las nueve treinta o diez cuarenta y cinco. ¿Qué día y hora le viene mejor?"
        
        elif any(word in message_lower for word in ['tarde', 'en la tarde']):
            response = "Tenemos horarios de tarde estos días: Lunes a las dos quince o tres treinta, Miércoles a las dos o cuatro quince, Viernes a la una treinta o tres cuarenta y cinco. ¿Qué día y hora le viene mejor?"
        
        # Confirmación de cita agendada para horarios específicos
        elif any(word in message_lower for word in ['nueve quince', '9:15', '9:15 am', 'nueve y cuarto']):
            response = "¡Perfecto! He agendado su cita para el Lunes 29 de Septiembre a las nueve quince de la mañana. Recibirá un correo de confirmación. ¿Necesita algo más?"
        
        elif any(word in message_lower for word in ['diez treinta', '10:30', '10:30 am', 'diez y media']):
            response = "¡Perfecto! He agendado su cita para el Lunes 29 de Septiembre a las diez treinta de la mañana. Recibirá un correo de confirmación. ¿Necesita algo más?"
        
        # ... (continuar con todos los horarios como en el código anterior)
        
        # Respuestas a preguntas específicas
        elif any(word in message_lower for word in ['qué pasa ahora', 'que pasa ahora', 'y ahora', 'qué sigue', 'que sigue']):
            response = "Si ya agendó su cita, recibirá un correo de confirmación. Si aún no ha terminado el proceso, podemos continuar con la descripción de su caso o la selección de horarios. ¿En qué paso necesita ayuda?"
        
        elif any(word in message_lower for word in ['cómo cancelo', 'como cancelo', 'cancelar cita']):
            response = "Para cancelar o reprogramar su cita, puede responder a este mensaje indicándolo o llamarnos al número de contacto que recibirá en el correo de confirmación."
        
        # Respuesta por defecto para mensajes cortos que no son descripciones
        elif len(message.strip()) <= 25:
            response = "¿Podría contarme un poco más sobre su situación? Necesito entender mejor su caso para poder ayudarle."
        
        else:
            response = "Entiendo. Para continuar, necesito que me ayude a completar la información de su caso. ¿Le gustaría que repita las opciones disponibles o prefiere contarme más detalles?"
        
        return jsonify({'response': response})
            
    except Exception as e:
        app.logger.error(f"Exception in chat: {str(e)}")
        return jsonify({'error': str(e)}), 500

        
@app.route('/api/health', methods=['GET'])
def health_check():
    """Endpoint para verificar el estado del servicio"""
    aws_configured = bool(AWS_ACCESS_KEY and AWS_SECRET_KEY)
    return jsonify({
        'status': 'healthy',
        'aws_configured': aws_configured,
        'aws_access_key_set': bool(AWS_ACCESS_KEY),
        'aws_secret_key_set': bool(AWS_SECRET_KEY),
        'service': 'Amazon Polly - Voz Legal Neuronal' if aws_configured else 'Modo emergencia - Navegador TTS'
    })

@app.route('/api/debug', methods=['GET'])
def debug_info():
    """Endpoint para debugging"""
    return jsonify({
        'aws_access_key_length': len(AWS_ACCESS_KEY) if AWS_ACCESS_KEY else 0,
        'aws_secret_key_length': len(AWS_SECRET_KEY) if AWS_SECRET_KEY else 0,
        'aws_region': AWS_REGION,
        'environment_variables': {k: v for k, v in os.environ.items() if 'AWS' in k}
    })

@app.route('/api/ssml-test', methods=['POST'])
def ssml_test():
    """Endpoint para probar diferentes configuraciones SSML"""
    try:
        data = request.json
        text = data.get('text', 'Hola, soy Claudia García, tu abogada virtual.')
        
        ssml_versions = {
            'neuronal_basico': create_ssml_text(text),
            'neuronal_avanzado': f"""
            <speak>
                <prosody rate="105%" pitch="+3%" volume="loud">
                    <amazon:effect name="drc">
                        <amazon:effect vocal-tract-length="+5%">
                            {add_natural_pauses(text)}
                        </amazon:effect>
                    </amazon:effect>
                </prosody>
            </speak>
            """,
            'con_enfasis': f"""
            <speak>
                <prosody rate="100%" pitch="+1%">
                    {improve_pronunciation(text)}
                </prosody>
            </speak>
            """
        }
        
        return jsonify({
            'original': text,
            'ssml_versions': ssml_versions
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
