/* Panel con los campos Fecha y Hora, usado para consultar o elegir una franja. */
import { field, h } from '../core/dom.js';
import { timeSlots, todayStr } from '../core/format.js';

/* Desplegable de horas (franjas de 30 minutos). Con allLabel añade una primera opción «sin filtro». */
export function timeSelect(value, allLabel) {
  const options = timeSlots().map((slot) => h('option', { value: slot }, slot));
  if (allLabel) options.unshift(h('option', { value: '' }, allLabel));
  return h('select', { name: 'time', value }, options);
}

/* min = primera fecha elegible (por defecto hoy; null permite fechas pasadas).
   allTimesLabel añade la opción «todas las horas». onChange se llama al cambiar fecha u hora. */
export function whenPanel({ date = todayStr(), time = '21:00', min = todayStr(), allTimesLabel, onChange } = {}) {
  const dateInput = h('input', { name: 'date', type: 'date', value: date, min, required: true });
  const timeInput = timeSelect(time, allTimesLabel);
  if (onChange) {
    dateInput.addEventListener('change', onChange);
    timeInput.addEventListener('change', onChange);
  }
  return {
    panel: h('div', { class: 'panel' }, h('div', { class: 'pair' }, field('Fecha', dateInput), field('Hora', timeInput))),
    date: dateInput,
    time: timeInput,
  };
}
