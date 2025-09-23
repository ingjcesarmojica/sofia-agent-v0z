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
        
        # Saludos y presentación
        if any(word in message_lower for word in ['hola', 'buenos días', 'buenas tardes', 'saludos', 'buenos', 'buenas']):
            response = "¡Bienvenido a TusAbogados.com! Estamos aquí para ofrecerle Asistencia Legal de forma inmediata. Si tiene una solicitud sobre derecho penal, familiar, civil, laboral o pensiones, está en el lugar correcto. ¡Su tranquilidad es nuestra prioridad!"        
       
        # Consultas sobre divorcio
        elif any(word in message_lower for word in ['divorcio', 'separación', 'separacion', 'matrimonio', 'esposo', 'esposa', 'cónyuge', 'conyugue']):
            response = "Entiendo que necesitas asesoría sobre divorcio. Te puedo ayudar con el proceso completo: evaluación de bienes conyugales, custodia de menores, pensión alimentaria y todos los trámites legales. ¿Tu situación requiere divorcio de mutuo acuerdo o contencioso?"
        
        # Consultas sobre custodia de menores
        elif any(word in message_lower for word in ['custodia', 'hijos', 'menor', 'menores', 'patria potestad', 'visitas', 'régimen de visitas']):
            response = "En temas de custodia, mi prioridad es siempre el bienestar superior del menor. Te asesoro sobre custodia compartida, patria potestad, régimen de visitas y modificación de acuerdos. ¿Cuál es la situación específica con tus hijos?"
        
        # Consultas sobre pensión alimentaria
        elif any(word in message_lower for word in ['pensión', 'pension', 'alimentaria', 'cuota alimentaria', 'cuota', 'alimentos', 'manutención', 'manutencion']):
            response = "Para pensión alimentaria, calculo el monto según los ingresos del obligado y las necesidades del beneficiario. Te ayudo a solicitarla, aumentarla, disminuirla o ejecutarla si hay incumplimiento. ¿Necesitas solicitar o modificar una pensión?"
        
        # Consultas sobre herencias y sucesiones
        elif any(word in message_lower for word in ['herencia', 'sucesión', 'sucesion', 'testamento', 'herederos', 'bienes', 'inventario', 'liquidación', 'liquidacion']):
            response = "En procesos sucesorales te asesoro sobre inventario y avalúo de bienes, liquidación de herencia, interpretación de testamentos y resolución de conflictos entre herederos. ¿El proceso es con o sin testamento?"
        
        # Consultas sobre derecho civil general
        elif any(word in message_lower for word in ['contrato', 'demanda', 'civil', 'responsabilidad', 'daños', 'perjuicios', 'incumplimiento']):
            response = "En derecho civil manejo contratos, responsabilidad civil, demandas por incumplimiento, daños y perjuicios, y resolución de conflictos patrimoniales. ¿Qué tipo de situación civil estás enfrentando?"
        
        # Consultas sobre derecho laboral
        elif any(word in message_lower for word in ['laboral', 'trabajo', 'despido', 'liquidación', 'liquidacion', 'acoso', 'discriminación', 'discriminacion']):
            response = "Te asesoro en temas laborales: despidos injustificados, cálculo de liquidaciones, acoso laboral, discriminación y protección de derechos del trabajador. ¿Qué situación laboral necesitas resolver?"
        
        # Consultas sobre honorarios y costos
        elif any(word in message_lower for word in ['precio', 'costo', 'honorarios', 'cuánto cuesta', 'cuanto cuesta', 'tarifa', 'valor', 'pago']):
            response = "Mis honorarios varían según la complejidad del caso. Ofrezco primera consulta gratuita donde evaluamos tu situación legal completa. Para casos complejos, manejo cuotas accesibles y planes de pago. ¿Te gustaría agendar tu consulta gratuita?"
        
        # Consultas sobre citas y consultas
        elif any(word in message_lower for word in ['consulta', 'cita', 'reunión', 'reunion', 'agendar', 'horario', 'disponibilidad']):
            response = "Perfecto, podemos agendar tu consulta legal. Ofrezco atención presencial en mi oficina y consultas virtuales. La primera consulta es completamente gratuita para evaluar tu caso. ¿Prefieres atención presencial o virtual?"
        
        # Consultas sobre documentos necesarios
        elif any(word in message_lower for word in ['documentos', 'papeles', 'necesito', 'llevar', 'requisitos', 'qué debo', 'que debo']):
            response = "Los documentos necesarios dependen de tu caso específico. Generalmente necesitamos: cédulas, certificados de matrimonio/nacimiento, escrituras de bienes, contratos relevantes y cualquier comunicación relacionada. En la consulta te daré la lista exacta."
        
        # Consultas sobre urgencias
        elif any(word in message_lower for word in ['urgente', 'emergencia', 'rápido', 'rapido', 'inmediato', 'ya', 'pronto']):
            response = "Entiendo que tu situación requiere atención urgente. Manejo casos de emergencia legal. Para situaciones críticas, podemos agendar consulta prioritaria el mismo día. ¿Puedes contarme brevemente qué situación urgente enfrentas?"
        
        # Consultas sobre medidas cautelares
        elif any(word in message_lower for word in ['cautelar', 'embargo', 'secuestro', 'protección', 'proteccion', 'medida', 'urgente']):
            response = "Las medidas cautelares protegen tus derechos durante el proceso legal. Puedo solicitar embargos, secuestros de bienes, medidas de protección y otras medidas preventivas según tu caso. ¿Qué bienes o derechos necesitas proteger?"
        
        # Consultas sobre violencia intrafamiliar
        elif any(word in message_lower for word in ['violencia', 'maltrato', 'agresión', 'agresion', 'amenaza', 'protección', 'proteccion']):
            response = "La violencia intrafamiliar es un tema muy serio. Te ayudo a solicitar medidas de protección inmediatas, denunciar ante las autoridades y proteger tus derechos y los de tus hijos. Tu seguridad es lo primero. ¿Estás en situación de riesgo actual?"
        
        # Agradecimientos
        elif any(word in message_lower for word in ['gracias', 'muchas gracias', 'agradezco', 'agradecido', 'agradecida', 'excelente', 'perfecto', 'muy bien']):
            response = "Ha sido un placer asesorarte. Como tu abogada, estaré aquí para proteger tus derechos legales cuando lo necesites. No dudes en contactarme para cualquier consulta jurídica adicional."
        
        # Respuesta por defecto
        else:
            responses = [
                "Como tu abogada, necesito conocer más detalles sobre tu situación legal para brindarte el mejor asesoramiento jurídico. ¿Podrías contarme específicamente qué problema legal enfrentas?",
                "Para proporcionarte una asesoría legal precisa y profesional, me gustaría conocer más sobre tu caso. ¿Se trata de un tema familiar, civil, laboral o de otra área del derecho?",
                "Cada caso legal es único y requiere análisis personalizado. Te sugiero agendar una consulta gratuita donde revisaremos todos los aspectos legales de tu situación. ¿Cuándo te vendría bien reunirnos?",
                "Mi experiencia me permite asesorarte en diversas áreas del derecho. Para brindarte la mejor estrategia legal, necesitaríamos revisar la documentación y detalles específicos de tu caso. ¿Te gustaría programar una cita?",
                "Entiendo tu consulta y quiero ayudarte de la mejor manera. En derecho, los detalles hacen la diferencia. ¿Podrías contarme más sobre los hechos y qué resultado buscas obtener?"
            ]
            response = responses[len(message) % len(responses)]
        
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
