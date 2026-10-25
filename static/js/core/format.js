/* Formato de importes, fechas y horas. */

export const euro = new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' });
export const people = (n) => `${n} ${n === 1 ? 'persona' : 'personas'}`;

const pad = (n) => String(n).padStart(2, '0');

/* Fecha de hoy en la zona horaria del dispositivo, como AAAA-MM-DD. */
export function todayStr() {
  const d = new Date();
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/* '2026-10-20' -> '20/10/2026' */
export function formatDate(iso) {
  const [year, month, day] = iso.split('-');
  return `${day}/${month}/${year}`;
}

/* El servidor guarda las horas en UTC ('2026-10-20T19:05:00Z'); aquí se pasan a la hora del móvil. */
export function formatTime(isoUtc) {
  const d = new Date(isoUtc);
  return `${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function formatDateTime(isoUtc) {
  const d = new Date(isoUtc);
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()} ${formatTime(isoUtc)}`;
}

/* Franjas de media hora, de 08:00 a 23:30. */
export function timeSlots() {
  const slots = [];
  for (let hour = 8; hour < 24; hour++) {
    for (const minutes of ['00', '30']) slots.push(`${pad(hour)}:${minutes}`);
  }
  return slots;
}
