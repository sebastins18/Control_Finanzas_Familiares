# Perfiles financieros de MisFinanzas

Los usuarios son cuentas de acceso y conservan el campo `rol` fijo:
`administrador` o `usuario`. Los perfiles financieros son una entidad distinta.

- `perfiles_financieros`: nombre y usuario propietario de cada perfil.
- `integrantes_perfil`: usuarios invitados a cada perfil. El propietario se
  determina por `id_propietario`, sin duplicarlo como invitado.
- Cuentas, categorías, movimientos, transferencias, presupuestos, metas, alertas
  y tipos de cambio utilizan `id_perfil`.
- Los movimientos de ahorro pertenecen al perfil por su meta y cuenta; los
  comprobantes, por su movimiento.
- Las monedas son un catálogo común; solo los administradores del sistema
  pueden modificarlo. Los tipos de cambio se guardan por perfil.

Las transferencias solicitan una cotización legible: **1 USD equivale a 460 CRC**.
Se ingresa únicamente `460`, con hasta dos decimales. El sistema determina la
dirección de la conversión según las monedas de las cuentas. Entre CRC y otra
moneda, esa otra moneda es la base; entre monedas extranjeras, la pantalla indica
la base elegida por su código ISO. No hay un selector de operación matemática.

La tabla `tipos_cambio` guarda `id_moneda_base`, `id_moneda_cotizada`, `cotizacion`,
fecha y perfil. Cada transferencia referencia una cotización independiente;
guardar otra cotización no altera la de una transferencia anterior. El listado
muestra, por ejemplo, **Cotización aplicada: 1 USD = 460,00 CRC**. El monto final
se redondea a centavos y se rechazan resultados menores de un centavo o superiores
al límite permitido.

La migración elimina las columnas direccionales anteriores, conserva los
identificadores y valores históricos exactos, y mantiene sus transferencias
asociadas. Las cotizaciones antiguas se presentan de forma legible; si requieren
redondeo al invertirlas para mostrarlas, se usa el símbolo **≈**. Sus valores
originales se mantienen para conservar las conversiones históricas.

## Uso

Después de iniciar sesión se muestra **Seleccionar perfil financiero**, con
las pestañas **Mis perfiles** e **Invitado**. Hay que elegir un perfil y pulsar
**Ingresar al perfil** antes de consultar o registrar información financiera.
La creación de perfiles está disponible en la administración de perfiles, no en
la pantalla de selección.

Desde el panel, la barra «Perfil financiero» permite **Cambiar perfil** o abrir
**Administrar perfiles / integrantes**.
Cualquier usuario puede crear y renombrar sus perfiles, seleccionar uno propio
o uno al que lo hayan invitado, y consultar su participación.

El propietario agrega invitados con su nombre de usuario de acceso. La cuenta
debe existir y estar activa; se agrega directamente, sin envío de correo ni
aceptación pendiente. Puede quitarles el acceso desde esa misma pantalla.

| Acción | Propietario | Invitado |
| --- | --- | --- |
| Consultar cuentas, movimientos, presupuestos, metas y alertas | Sí | Sí |
| Registrar ingresos, gastos, transferencias y movimientos de ahorro | Sí | Sí |
| Adjuntar y consultar comprobantes | Sí | Sí |
| Marcar alertas como leídas | Sí | Sí |
| Editar o eliminar operaciones existentes | Sí | No |
| Crear o modificar cuentas, categorías, presupuestos y metas | Sí | No |
| Crear, editar o eliminar alertas manuales | Sí | No |
| Renombrar el perfil o administrar sus integrantes | Sí | No |

Los permisos se comprueban en el servidor, además de ocultar los controles que
no correspondan. El rol global de administrador gestiona cuentas de acceso y el
catálogo de monedas; no sustituye la propiedad ni la invitación de un perfil.

Para invitados, el menú identifica presupuestos, metas, cuentas, categorías y
monedas como **Consulta**, y agrupa los catálogos bajo **Consultas**. Estas
pantallas no muestran formularios de mantenimiento ni columnas de acciones
vacías. El acceso a perfiles se llama **Mis perfiles**; solo aparecen controles
de administración en aquellos perfiles donde la persona es propietaria.

La selección se guarda en la sesión, no en `app_config` ni como configuración
global. Dos usuarios, o dos sesiones de un mismo usuario, pueden tener perfiles
distintos seleccionados. Al quitar una invitación, el acceso se revisa en la
siguiente solicitud y se solicita seleccionar otro perfil disponible. No se borran las
operaciones registradas por esa persona.

Se permite eliminar únicamente perfiles vacíos, sin operaciones, presupuestos,
metas ni saldos iniciales. Debe conservarse al menos un perfil propio. Las cuentas
y categorías iniciales del perfil vacío se eliminan junto a él.

## Migración

Al iniciar sobre el esquema anterior, se crea un respaldo SQLite junto a la base
con el patrón `finanzas.antes-usuarios-<fecha>.sqlite3`. Se crea un perfil propio
por usuario y se trasladan sus relaciones financieras a `id_perfil`, conservando
identificadores, importes, fechas, comprobantes y estados de lectura. El cambio
de tablas se realiza dentro de una transacción con comprobación de claves
foráneas. Los tipos de cambio históricos comunes se copian a los perfiles y las
transferencias quedan enlazadas a la copia correspondiente.

La migración se ejecuta una sola vez. Los usuarios nuevos reciben un perfil
inicial, con categorías y cuentas para comenzar. Cada perfil adicional comienza
con sus propios catálogos iniciales y sin operaciones.

Ejemplo: Luis abre su perfil con los datos existentes y agrega a Miriam como
invitada. Miriam selecciona ese perfil desde `/perfiles`; ambos pueden registrar
operaciones allí. El perfil personal de Miriam permanece independiente.
