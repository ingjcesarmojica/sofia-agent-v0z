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
            # Reiniciar variables de sesión
            for attr in ['user_name', 'user_email', 'user_phone', 'case_description', 'appointment_time', 'user_role', 'case_category']:
                if hasattr(chat, attr):
                    delattr(chat, attr)
            
            response = """¡Bienvenido a TusAbogados.com! Para personalizar su atención, ¿con quién tengo el gusto de hablar?

Por favor, dígame su nombre."""
       
        # Captura del nombre - Pregunta por el rol
        elif not hasattr(chat, 'user_name') and len(message.strip()) > 2:
            chat.user_name = message.strip()
            response = f"""Mucho gusto {chat.user_name}. Para orientarle mejor, necesito saber su rol en el caso.

¿Es usted:
- "Víctima": por ejemplo, si sufrió un accidente de tránsito, le deben dinero, fue estafado, o sufrió algún daño o perjuicio.
- "Demandante": por ejemplo, si quiere iniciar una demanda por divorcio, reclamar una herencia, demandar por incumplimiento de contrato, o exigir sus derechos laborales.

¿Se considera víctima o demandante en esta situación?"""
        
        # Captura del rol - Pregunta por categoría
        elif not hasattr(chat, 'user_role') and any(word in message_lower for word in ['víctima', 'victima', 'demandante']):
            if 'víctima' in message_lower or 'victima' in message_lower:
                chat.user_role = 'víctima'
            else:
                chat.user_role = 'demandante'
                
            response = f"""Entendido {getattr(chat, 'user_name', '')}, como {chat.user_role}. Ahora necesito saber el tipo de caso.

Por ejemplo:
- "Categoría Civil": si quiere demandar por divorcio, reclamar una herencia, exigir cumplimiento de contrato, o resolver problemas de propiedad.
- "Categoría Laboral": por ejemplo si va a demandar por despido injustificado, acoso laboral, o para reclamar prestaciones laborales.  
- "Categoría Penal": si va a denunciar por robos, agresiones, amenazas, o estafas.

Si no está seguro a qué categoría pertenece su caso, puede decir: "No sé cuál es mi categoría" o "La desconozco".

¿En qué categoría cree que está su caso?"""
        
        # Captura de categoría - Pide descripción breve
        elif not hasattr(chat, 'case_category') and any(word in message_lower for word in ['civil', 'laboral', 'penal', 'no sé', 'no se', 'desconozco']):
            if 'civil' in message_lower:
                chat.case_category = 'civil'
            elif 'laboral' in message_lower:
                chat.case_category = 'laboral'
            elif 'penal' in message_lower:
                chat.case_category = 'penal'
            else:
                chat.case_category = 'no definida'
            
            response = f"""Categoría {chat.case_category} registrada. 

Por favor, descríbame brevemente su caso para entender mejor su situación."""
        
        # Captura descripción - Pide correo electrónico
        elif not hasattr(chat, 'user_email') and hasattr(chat, 'case_category') and len(message.strip()) > 10:
            chat.case_description = message.strip()
            response = f"""Gracias {getattr(chat, 'user_name', '')} por la información. 

Para agendar su cita y enviarle la confirmación, necesito su correo electrónico.

¿Cuál es su correo electrónico?"""
        
        # Captura del email - SIN VALIDACIÓN, cualquier respuesta se acepta
        elif not hasattr(chat, 'user_email'):
            # Cualquier respuesta se toma como email
            chat.user_email = message.strip()
            response = f"""Correo registrado correctamente.

Ahora necesito un número de teléfono para contactarle.

¿Cuál es su número de contacto?"""
        
        # Captura del teléfono - Cualquier respuesta con números
        elif not hasattr(chat, 'user_phone'):
            chat.user_phone = message.strip()
            response = f"""¡Perfecto {getattr(chat, 'user_name', '')}! Tenemos toda la información necesaria.

Le propongo el primer horario disponible:
¿Le viene bien el Lunes 29 de Septiembre a las 10:30 de la mañana?

Responda "sí" para confirmar o "no" para otro horario."""
        
        # Confirmación de primer horario
        elif not hasattr(chat, 'appointment_time') and any(word in message_lower for word in ['sí', 'si', 'ok', 'de acuerdo', 'confirmo', 'sí acepto', 'si acepto']):
            chat.appointment_time = "Lunes 29 de Septiembre - 10:30 am"
            response = f"""¡Cita confirmada {getattr(chat, 'user_name', '')}!

📅 Fecha: Lunes 29 de Septiembre - 10:30 am
📧 Confirmación enviada a: {getattr(chat, 'user_email', '')}
📞 Teléfono de contacto: {getattr(chat, 'user_phone', '')}

Recuerde: si su caso supera los 10 millones, no hay costo inicial. Solo paga el 10% si recuperamos su dinero.

¿Hay algo más en lo que pueda ayudarle?"""
        
        # Rechazo del primer horario - Ofrece segundo
        elif not hasattr(chat, 'appointment_time') and any(word in message_lower for word in ['no', 'no me viene', 'otro horario', 'otra hora']):
            response = """Entiendo. Le propongo:
Miércoles 1 de Octubre a las 3:30 de la tarde.

¿Le funciona este horario?"""
        
        # Confirmación de segundo horario
        elif not hasattr(chat, 'appointment_time') and any(word in message_lower for word in ['miércoles', 'miercoles', 'sí miércoles', 'si miercoles', '3:30']):
            chat.appointment_time = "Miércoles 1 de Octubre - 3:30 pm"
            response = f"""¡Cita confirmada {getattr(chat, 'user_name', '')}!

📅 Fecha: Miércoles 1 de Octubre - 3:30 pm
📧 Confirmación enviada a: {getattr(chat, 'user_email', '')}
📞 Teléfono de contacto: {getattr(chat, 'user_phone', '')}

¿Hay algo más en lo que pueda ayudarle?"""
        
        # Respuesta NEGATIVA a "¿algo más?" - CIERRE AUTOMÁTICO
        elif hasattr(chat, 'appointment_time') and any(word in message_lower for word in ['no', 'nada más', 'eso es todo', 'no gracias', 'listo', 'ya está', 'ya esta']):
            response = f"""¡Perfecto {getattr(chat, 'user_name', '')}! 

Ha sido un placer ayudarle. Un abogado se contactará con usted en la fecha acordada.

**Esta llamada se finalizará automáticamente. ¡Que tenga un excelente día!**

[LLAMADA FINALIZADA]"""
        
        # Consulta adicional después de cita confirmada
        elif hasattr(chat, 'appointment_time') and len(message.strip()) > 5:
            response = f"""Entendido {getattr(chat, 'user_name', '')}. 

He registrado su consulta adicional. Uno de nuestros abogados especializados se contactará con usted según los datos agendados y le ampliará toda la información al respecto.

¿Hay alguna otra cosa en la que pueda asistirle?"""
        
        # Solicitud de repetición contextual
        elif any(word in message_lower for word in ['repetir', 'repita', 'no entendí']):
            if not hasattr(chat, 'user_name'):
                response = "Por favor, dígame su nombre para continuar."
            elif not hasattr(chat, 'user_role'):
                response = "¿Se considera víctima o demandante en este caso?"
            elif not hasattr(chat, 'case_category'):
                response = "¿En qué categoría está su caso: civil, laboral o penal?"
            elif not hasattr(chat, 'user_email'):
                response = "Necesito su correo electrónico para enviarle la confirmación."
            elif not hasattr(chat, 'user_phone'):
                response = "Necesito su número de teléfono para contactarle."
            elif not hasattr(chat, 'appointment_time'):
                response = "¿Le viene bien el Lunes 29 de Septiembre a las 10:30 de la mañana?"
            else:
                response = "¿Hay algo más en lo que pueda ayudarle?"
        
        # Agradecimientos y cierre automático
        elif any(word in message_lower for word in ['gracias', 'adiós', 'chao', 'hasta luego']):
            response = f"""Gracias a usted {getattr(chat, 'user_name', '')}. 

**Esta llamada se finalizará automáticamente. ¡Que tenga un excelente día!**

[LLAMADA FINALIZADA]"""
        
        # Respuesta por defecto - Guía al siguiente paso
        else:
            if not hasattr(chat, 'user_name'):
                response = "Por favor, dígame su nombre para continuar."
            elif not hasattr(chat, 'user_role'):
                response = "¿Se considera víctima o demandante en este caso?"
            elif not hasattr(chat, 'case_category'):
                response = "¿En qué categoría está su caso: civil, laboral o penal?"
            elif not hasattr(chat, 'user_email'):
                response = "Necesito su correo electrónico para enviarle la confirmación."
            elif not hasattr(chat, 'user_phone'):
                response = "Necesito su número de teléfono para contactarle."
            elif not hasattr(chat, 'appointment_time'):
                response = "¿Le viene bien el Lunes 29 de Septiembre a las 10:30 de la mañana?"
            else:
                response = "¿Hay algo más en lo que pueda ayudarle?"
        
        return jsonify({
            'response': response,
            'end_call': '[LLAMADA FINALIZADA]' in response
        })
            
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
