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
