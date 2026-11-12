# Roadmap de mejoras futuras

**Versión final: `v1.0.0` — viernes 13 de noviembre de 2026.**

Las mejoras siguientes son propuestas futuras para la evolución de MisFinanzas. Los horizontes orientan su evaluación y priorización; no describen funcionalidades ya implementadas ni compromisos aprobados por el equipo o la universidad.

## Un mes — diciembre de 2026

La prioridad propuesta es mejorar la experiencia de uso y reforzar la protección y recuperación de la información.

- **Usabilidad y accesibilidad:** revisar navegación, formularios, mensajes de validación, uso mediante teclado y legibilidad con personas usuarias de prueba.
- **Seguridad de sesiones y controles de acceso:** ampliar la protección CSRF, revisar la caducidad e invalidación de sesiones, los límites de intentos de acceso y los permisos por rol y perfil.
- **Recuperación segura de contraseñas:** diseñar un mecanismo con verificación de identidad, vigencia limitada y uso único de las solicitudes, sin revelar si una cuenta existe. La recuperación actual requiere la intervención de un administrador.
- **Restauración de datos:** realizar pruebas con copias de seguridad en bases aisladas y documentar el procedimiento, las incidencias y la integridad de los datos recuperados.

**Verificación prevista:** pruebas de usabilidad, seguridad, permisos y recuperación de información. Registrar resultados y contrastar la restauración con los registros originales de SQLite antes de habilitar cambios para usuarios.

## Seis meses — mayo de 2027

La prioridad propuesta es ampliar el análisis financiero y mejorar la operación de la aplicación, apoyándose en las medidas del primer horizonte.

- **Gráficos y comparaciones financieras:** representar ingresos y gastos por período y categoría, respetando la separación de monedas y perfiles.
- **Reportes, exportaciones y notificaciones:** ampliar los reportes y las salidas CSV existentes y evaluar alertas por correo, por ejemplo, al superar presupuestos. Evitar duplicar las alertas visuales actuales del 80 % y 100 % y comprobar los permisos de acceso a cada resultado.
- **Monitoreo, sesiones y copias de seguridad:** mejorar la supervisión del proceso, evaluar sesiones persistentes y organizar respaldos con verificación y pruebas de restauración periódicas.

**Verificación prevista:** contrastar gráficos, comparaciones, reportes y exportaciones con los registros de SQLite y comprobar las nuevas funcionalidades. Verificar también el envío de notificaciones, el aislamiento entre perfiles y la recuperación de las copias de seguridad.

Como opciones de ampliación sujetas a necesidades reales, puede evaluarse la consulta automática de tipos de cambio mediante un servicio externo y otras integraciones.

## Posible TFG

- Investigar patrones de ingresos y gastos.
- Estudiar herramientas de apoyo a la planificación financiera.
- Explorar recomendaciones personalizadas y explicables, diferenciándolas de asesoramiento financiero profesional.

**Verificación prevista:** propuesta de investigación con metodología, evaluación de usabilidad y protección de datos, sujeta a aprobación universitaria. Definir consentimiento, datos de evaluación y criterios de utilidad y explicación antes de utilizar información personal.

## Estado actual y seguimiento

Estado actual: MisFinanzas cuenta con pruebas automatizadas, historial de movimientos, reporte anual, exportación CSV y respaldos de SQLite. También dispone de alertas visuales de presupuesto al 80 % y 100 %, que podrían ampliarse mediante notificaciones por correo electrónico.

Las mejoras propuestas se evaluarán según las necesidades de las personas usuarias y las prioridades del equipo. Cada incorporación deberá acompañarse de pruebas que permitan verificar su funcionamiento, seguridad y compatibilidad con las funcionalidades existentes.