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
        
        message_lower = message.lower()
        
        # Saludo inicial - Pide el nombre
        if any(word in message_lower for word in ['hola', 'buenos días', 'buenas tardes', 'saludos', 'buenos', 'buenas', 'iniciar', 'empezar']):
            response = """¡Bienvenido a TusAbogados.com! Para personalizar su atención, ¿con quién tengo el gusto de hablar?

Por favor, dígame su nombre."""
       
        # Captura del nombre - Pregunta por el rol
        elif not hasattr(chat, 'user_name') and len(message.strip()) > 2 and not any(word in message_lower for word in ['víctima', 'victima', 'demandante', 'no', 'sí', 'si']):
            chat.user_name = message.strip()
            response = f"""Mucho gusto {chat.user_name}. Para orientarle mejor, necesito saber su rol en el caso.

Por ejemplo:
- Si sufrió un accidente o le deben dinero, sería "víctima"
- Si quiere demandar a alguien por incumplimiento, sería "demandante"

¿Cuál es su situación: víctima o demandante?"""
        
        # Rol: Víctima - Pregunta por categoría
        elif any(word in message_lower for word in ['víctima', 'victima', 'soy víctima', 'soy victima']):
            response = """Entiendo que es víctima. Ahora necesito saber el tipo de caso.

Por ejemplo:
- "Civil": problemas familiares, contratos, propiedades
- "Laboral": despido, acoso, derechos laborales  
- "Penal": robos, agresiones, estafas
- "No sé cuál es mi categoría": si no está seguro

¿En qué categoría está su caso?"""
        
        # Rol: Demandante - Pregunta por categoría
        elif any(word in message_lower for word in ['demandante', 'soy demandante']):
            response = """Entiendo que es demandante. Ahora necesito saber el tipo de caso.

Por ejemplo:
- "Civil": divorcio, herencias, contratos
- "Laboral": demanda por despido, liquidación
- "Penal": denuncia por agresión, estafa
- "No sé cuál es mi categoría": si no está seguro

¿En qué categoría está su caso?"""
        
        # Categorías del caso
        elif any(word in message_lower for word in ['civil']):
            response = "Caso civil registrado. Cuénteme brevemente: ¿qué problema tiene con contratos, familia o propiedades?"
        
        elif any(word in message_lower for word in ['laboral']):
            response = "Caso laboral registrado. Cuénteme brevemente: ¿qué situación tiene con su trabajo o empleador?"
        
        elif any(word in message_lower for word in ['penal']):
            response = "Caso penal registrado. Cuénteme brevemente: ¿qué hecho delictivo o infracción ocurrió?"
        
        elif any(word in message_lower for word in ['no sé', 'no se', 'no estoy seguro', 'no estoy segura', 'no sé cuál', 'no se cual']):
            response = "No hay problema. Cuénteme brevemente qué está sucediendo y le ayudo a identificar la categoría."
        
        # Descripción del caso - Pide correo electrónico
        elif len(message.strip()) > 20 and not hasattr(chat, 'user_email'):
            chat.case_description = message.strip()
            response = f"""Gracias {getattr(chat, 'user_name', '')} por la información. Un abogado especializado revisará su caso.

Para agendar su cita, necesito su correo electrónico para enviarle la confirmación.

¿Cuál es su correo electrónico?"""
        
        # Captura del email - Pide teléfono
        elif '@' in message and '.' in message and not hasattr(chat, 'user_phone'):
            chat.user_email = message.strip()
            response = f"""Correo registrado correctamente.

Ahora necesito un número de teléfono para contactarle en caso necesario.

¿Cuál es su número de contacto?"""
        
        # Captura del teléfono - Ofrece primer horario
        elif any(char.isdigit() for char in message) and len(message.replace(' ', '').replace('-', '')) >= 7 and not hasattr(chat, 'appointment_time'):
            chat.user_phone = message.strip()
            response = f"""¡Perfecto {getattr(chat, 'user_name', '')}! Tenemos toda la información necesaria.

Le propongo el primer horario disponible:
¿Le viene bien el Lunes 29 de Septiembre a las 10:30 de la mañana?

Responda "sí" para confirmar o "no" para otro horario."""
        
        # Confirmación de primer horario
        elif any(word in message_lower for word in ['sí', 'si', 'ok', 'de acuerdo', 'confirmo', 'sí acepto', 'si acepto']):
            chat.appointment_time = "Lunes 29 de Septiembre - 10:30 am"
            response = f"""¡Cita confirmada {getattr(chat, 'user_name', '')}!

📅 Fecha: Lunes 29 de Septiembre - 10:30 am
📧 Confirmación enviada a: {getattr(chat, 'user_email', '')}
📞 Teléfono de contacto: {getattr(chat, 'user_phone', '')}

Recuerde: si su caso supera los 10 millones, no hay costo inicial. Solo paga el 10% si recuperamos su dinero.

Un abogado se contactará con usted. ¿Necesita algo más?"""
        
        # Rechazo del primer horario - Ofrece segundo
        elif any(word in message_lower for word in ['no', 'no me viene', 'otro horario', 'otra hora']):
            response = """Entiendo. Le propongo:
Miércoles 1 de Octubre a las 3:30 de la tarde.

¿Le funciona este horario?"""
        
        # Confirmación de segundo horario
        elif any(word in message_lower for word in ['miércoles', 'miercoles', 'sí miércoles', 'si miercoles', '3:30']):
            chat.appointment_time = "Miércoles 1 de Octubre - 3:30 pm"
            response = f"""¡Cita confirmada {getattr(chat, 'user_name', '')}!

📅 Fecha: Miércoles 1 de Octubre - 3:30 pm
📧 Confirmación enviada a: {getattr(chat, 'user_email', '')}
📞 Teléfono de contacto: {getattr(chat, 'user_phone', '')}

Un abogado especializado se contactará con usted. ¿Necesita algo más?"""
        
        # Solicitud de repetición
        elif any(word in message_lower for word in ['repetir', 'repita', 'no entendí']):
            current_step = "nombre"
            if hasattr(chat, 'user_name'):
                current_step = "rol"
            if hasattr(chat, 'case_description'):
                current_step = "contacto"
            
            if current_step == "nombre":
                response = "Por favor, dígame su nombre para continuar."
            elif current_step == "rol":
                response = "¿Es víctima o demandante en este caso?"
            else:
                response = "¿Podría proporcionarme su correo electrónico para la confirmación?"
        
        # Reiniciar conversación
        elif any(word in message_lower for word in ['nuevo caso', 'otro caso', 'empezar de nuevo']):
            # Limpiar variables de sesión
            for attr in ['user_name', 'user_email', 'user_phone', 'case_description', 'appointment_time']:
                if hasattr(chat, attr):
                    delattr(chat, attr)
            response = "¡Claro! Comencemos con un nuevo caso. ¿Cuál es su nombre?"
        
        # Agradecimientos y cierre
        elif any(word in message_lower for word in ['gracias', 'listo', 'eso es todo', 'nada más', 'adiós', 'chao']):
            response = f"""Ha sido un placer atenderle {getattr(chat, 'user_name', '')}. 

Si necesita algo más, estoy aquí para ayudarle. ¡Que tenga un excelente día!"""
        
        # Respuesta por defecto
        else:
            response = "¿Podría ser más específico? Necesito esta información para agendar su cita con el abogado."
        
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
