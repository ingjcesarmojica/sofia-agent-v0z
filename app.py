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
        
        # Saludo inicial - Pregunta por el rol con ejemplos
        if any(word in message_lower for word in ['hola', 'buenos días', 'buenas tardes', 'saludos', 'buenos', 'buenas', 'iniciar', 'empezar']):
            response = """¡Bienvenido a TusAbogados.com! Para orientarle mejor, necesito saber su rol en el caso.

Por ejemplo:
- Si sufrió un accidente o le deben dinero, sería "víctima"
- Si quiere demandar a alguien por incumplimiento, sería "demandante"

¿Cuál es su situación: víctima o demandante?"""
       
        # Rol: Víctima - Pregunta por categoría con ejemplos
        elif any(word in message_lower for word in ['víctima', 'victima', 'soy víctima', 'soy victima']):
            response = """Entiendo que es víctima. Ahora necesito saber el tipo de caso.

Por ejemplo:
- "Civil": problemas familiares, contratos, propiedades
- "Laboral": despido, acoso, derechos laborales  
- "Penal": robos, agresiones, estafas
- "No sé cuál es mi categoría": si no está seguro

¿En qué categoría está su caso?"""
        
        # Rol: Demandante - Pregunta por categoría con ejemplos
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
        
        # Descripción del caso - Ofrece primer horario
        elif len(message.strip()) > 20:
            response = """Gracias por la información. Un abogado especializado revisará su caso.

Le propongo el primer horario disponible:
¿Le viene bien el Lunes 29 de Septiembre a las 10:30 de la mañana?

Responda "sí" para confirmar, "no" para otro horario, o "mejor tarde" si prefiere la tarde."""
        
        # Confirmación de primer horario
        elif any(word in message_lower for word in ['sí', 'si', 'ok', 'de acuerdo', 'confirmo', 'sí acepto', 'si acepto']):
            response = """¡Perfecto! Cita confirmada para el Lunes 29 de Septiembre a las 10:30 am.

Recuerde: si su caso supera los 10 millones, no hay costo inicial. Solo paga el 10% si recuperamos su dinero.

Recibirá un correo con los detalles. ¿Necesita algo más?"""
        
        # Rechazo del primer horario - Ofrece segundo
        elif any(word in message_lower for word in ['no', 'no me viene', 'otro horario', 'otra hora']):
            response = """Entiendo. Le propongo:
Miércoles 1 de Octubre a las 3:30 de la tarde.

¿Le funciona este horario?"""
        
        # Prefiere horario de tarde
        elif any(word in message_lower for word in ['tarde', 'mejor tarde', 'en la tarde']):
            response = """De acuerdo. Horarios de tarde disponibles:
- Lunes 29 a las 3:30 pm
- Miércoles 1 a las 4:15 pm  
- Viernes 3 a las 3:45 pm

¿Cuál prefiere?"""
        
        # Confirmación de segundo horario
        elif any(word in message_lower for word in ['miércoles', 'miercoles', 'sí miércoles', 'si miercoles']):
            response = """¡Perfecto! Cita confirmada para el Miércoles 1 de Octubre a las 3:30 pm.

Recuerde: si su caso supera los 10 millones, no hay costo inicial. Solo paga el 10% si recuperamos su dinero.

Recibirá un correo con los detalles. ¿Necesita algo más?"""
        
        # Selección de horario específico
        elif any(word in message_lower for word in ['lunes', 'viernes', '3:30', '4:15', '3:45']):
            response = "¡Cita confirmada! Recibirá un correo con los detalles. ¿Necesita algo más?"
        
        # Solicitud de repetición contextual
        elif any(word in message_lower for word in ['repetir', 'repita', 'no entendí']):
            response = "¿Qué le gustaría que repita: las opciones de rol, las categorías de caso, o los horarios disponibles?"
        
        # Repetir opciones de rol
        elif any(word in message_lower for word in ['rol', 'opciones de rol']):
            response = "Las opciones son: víctima (si sufrió un daño) o demandante (si inicia una demanda). ¿Cuál es su caso?"
        
        # Repetir categorías
        elif any(word in message_lower for word in ['categorías', 'categorias', 'tipos de caso']):
            response = "Categorías: civil (familia, contratos), laboral (trabajo), penal (delitos), o no sé cuál es. ¿En cuál está su caso?"
        
        # Repetir horarios
        elif any(word in message_lower for word in ['horarios', 'fechas']):
            response = "Horarios disponibles: Lunes 29, Miércoles 1 o Viernes 3. ¿Qué día le viene mejor?"
        
        # Consultas específicas que interrumpen el flujo
        elif any(word in message_lower for word in ['divorcio', 'custodia', 'pensión', 'herencia', 'despido']):
            response = "Entiendo su consulta. Para darle una respuesta precisa, necesito primero completar su registro. ¿Podemos continuar con la información del caso?"
        
        # Agradecimientos y cierre
        elif any(word in message_lower for word in ['gracias', 'listo', 'eso es todo', 'nada más']):
            response = "Ha sido un placer ayudarle. Si necesita algo más, estoy aquí. ¡Que tenga un excelente día!"
        
        # Respuesta por defecto para continuar el flujo
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
