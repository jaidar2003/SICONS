# SICONS - Idea del proyecto

## Resumen

SICONS es un sistema de apoyo a la toma de decisiones para la compra de materiales de construccion.

El objetivo no es solamente registrar precios, sino transformar facturas, listas de precios y datos historicos en informacion util para decidir mejor:

- cuando comprar
- cuanto podria aumentar un material
- como impacta ese aumento en una obra
- que materiales conviene priorizar
- cuanto se podria ahorrar comprando antes

La idea central es convertir datos dispersos de compras en inteligencia de compras para obras chicas y medianas.

## Problema

En obras y compras de materiales suele pasar que los precios cambian con frecuencia, las presentaciones comerciales varian y la informacion historica queda desordenada en facturas, presupuestos o planillas.

Esto genera varios problemas:

- no se sabe con claridad cuanto aumento un material
- cuesta comparar precios cuando cambia la presentacion, por ejemplo bolsa de 50 kg a 25 kg
- no hay una base historica limpia para analizar tendencias
- se toman decisiones de compra sin medir el impacto futuro
- es dificil justificar si conviene comprar ahora o esperar
- el presupuesto de obra queda expuesto a aumentos no anticipados

SICONS busca resolver ese problema desde una perspectiva practica: ordenar datos reales, normalizarlos y usarlos para apoyar decisiones.

## Usuario principal

El usuario principal es el comprador de materiales o responsable de compras de una obra.

Puede ser:

- una constructora chica o mediana
- un arquitecto que administra obras
- un maestro mayor de obra
- una empresa de mantenimiento
- un encargado de compras
- un desarrollador chico
- un municipio o area de obras con compras recurrentes

Este usuario necesita saber como evolucionan los precios y como esa evolucion afecta sus decisiones.

## Usuario secundario

El usuario secundario es el administrador o duenio del sistema.

Su funcion no es el centro del negocio, pero es necesaria para mantener la informacion:

- cargar precios historicos
- registrar fuentes
- administrar materiales
- administrar presentaciones
- corregir datos
- mantener la base confiable

La carga de datos es un medio. El valor principal esta en el analisis que recibe el comprador.

## Propuesta de valor

SICONS permite anticipar el impacto de los aumentos de materiales antes de comprar.

En vez de responder solamente:

```text
cuanto cuesta hoy el cemento
```

busca responder:

```text
cuanto aumento
cuanto podria costar mas adelante
cuanto me impacta si necesito cierta cantidad
me conviene comprar ahora o esperar
que material representa mayor riesgo de aumento
```

La propuesta de valor se apoya en tres pilares:

1. Normalizacion de precios.
2. Analisis historico.
3. Proyeccion del impacto economico.

## Diferenciador

El diferencial de SICONS no es simplemente mostrar una tabla de precios.

El diferencial es combinar:

- datos reales de facturas o listas
- normalizacion por unidad comparable
- visualizacion historica
- prediccion de precios
- simulacion de costos futuros
- comparacion entre comprar ahora y comprar despues

Por ejemplo, si el sistema estima un precio futuro de cemento por kg, puede transformarlo automaticamente en:

```text
precio estimado por bolsa de 25 kg
precio estimado por bolsa de 50 kg
costo para 100 bolsas
diferencia contra comprar hoy
porcentaje esperado de aumento
```

Eso convierte un dato de precio en una decision de compra.

## Modelo de negocio posible

La mejor forma de pensar SICONS como negocio es como un SaaS B2B liviano orientado a compras de materiales de construccion.

### Clientes potenciales

- constructoras chicas y medianas
- estudios de arquitectura
- empresas de mantenimiento
- administradores de consorcios grandes
- desarrolladores chicos
- responsables de compras de obra
- areas de obras publicas de pequena escala

### Plan basico

Pensado para usuarios que quieren ordenar y consultar precios.

Incluye:

- carga manual de precios
- historial por material
- normalizacion automatica
- filtros por periodo
- grafico historico
- variaciones porcentuales

### Plan profesional

Pensado para compradores recurrentes.

Incluye:

- multiples usuarios
- mas materiales
- importacion de facturas
- predicciones a distintos horizontes
- simulador de compra futura
- comparacion comprar ahora vs comprar despues
- exportacion de reportes

### Plan empresa

Pensado para organizaciones con procesos mas formales.

Incluye:

- multiples obras
- roles y permisos
- alertas de aumentos
- reportes ejecutivos
- integracion con proveedores o sistemas internos
- soporte

## Alcance MVP

El MVP debe enfocarse en demostrar el valor central del sistema sin intentar resolver todo desde el inicio.

El flujo minimo seria:

1. Cargar materiales y presentaciones.
2. Cargar precios historicos con fecha, fuente y comprobante.
3. Normalizar precios segun unidad base.
4. Consultar la serie historica de un material.
5. Filtrar por periodo.
6. Visualizar grafico historico.
7. Mostrar variaciones porcentuales.
8. Proyectar precio futuro.
9. Calcular impacto segun cantidad necesaria.
10. Comparar comprar ahora vs comprar despues.

Con ese flujo, SICONS ya se puede presentar como una herramienta de apoyo a decisiones de compra.

## Alcance futuro

Una vez validado el MVP, el producto podria crecer hacia:

- predicciones mas robustas
- deteccion de anomalias
- alertas automaticas
- carga masiva desde facturas
- lectura automatica de PDFs o imagenes de facturas
- comparacion entre proveedores
- presupuesto por obra
- planificacion de compras por etapa
- recomendaciones de momento optimo de compra
- asistente conversacional para consultar precios y proyecciones

## Enfoque para la tesis

Para una tesis, SICONS puede defenderse como:

```text
Sistema de apoyo a la toma de decisiones para la compra de materiales de construccion, basado en normalizacion de precios historicos, analisis de evolucion y proyeccion de costos futuros.
```

El foco academico fuerte esta en:

- modelado de datos historicos
- normalizacion de precios por unidad comparable
- trazabilidad de fuentes
- analisis temporal
- prediccion
- impacto economico sobre decisiones de compra

No se trata solo de hacer un CRUD de materiales. El valor esta en convertir datos historicos en informacion accionable.

## Frase corta del producto

```text
SICONS ayuda a anticipar aumentos de materiales y decidir mejor cuando comprar.
```

## Frase comercial

```text
Inteligencia de compras para obras: analiza precios historicos, proyecta aumentos y estima el impacto futuro en tu presupuesto.
```

