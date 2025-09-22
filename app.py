import os
import requests
import base64
import boto3
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import logging
from botocore.exceptions import BotoCoreError, ClientError

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
        
        # Verificación DIRECTA de credenciales (como en appguia.py)
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
        
        # Sintetizar voz con Polly - voz femenina profesional
        app.logger.info(f"Sintetizando texto: {text[:50]}...")
        response = polly.synthesize_speech(
            Text=text,
            OutputFormat='mp3',
            VoiceId='Lupe'      # Voz femenina en español latino
        )
        
        app.logger.info("Audio sintetizado correctamente")
        
        # Convertir audio a base64
        audio_data = response['AudioStream'].read()
        audio_content = base64.b64encode(audio_data).decode('utf-8')
        
        return jsonify({
            'audioContent': audio_content,
            'audioUrl': f"data:audio/mp3;base64,{audio_content}",
            'useBrowserTTS': False
        })
            
    except (BotoCoreError, ClientError) as error:
        app.logger.error(f"AWS Polly error: {error}")
        # Fallback a modo navegador si hay error de AWS
        return jsonify({
            'audioContent': None,
            'audioUrl': None,
            'useBrowserTTS': True,
            'text': text,
            'error': str(error)
        })
    except Exception as e:
        app.logger.error(f"Exception in speak_text: {str(e)}")
        # Fallback a modo navegador para cualquier otro error
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
            response = "Hola, soy Claudia García, abogada especializada en derecho civil y familiar. Estoy aquí para brindarte asesoría legal profesional. ¿En qué asunto legal puedo ayudarte hoy?"
        
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
        'service': 'Amazon Polly - Voz Legal' if aws_configured else 'Modo emergencia - Navegador TTS'
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
