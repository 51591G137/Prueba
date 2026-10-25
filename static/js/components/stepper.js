/* Selector de cantidad: [−] 2 [+] */
import { h } from '../core/dom.js';

export function stepper({ value = 0, min = 0, max = 99, label, onChange }) {
  let current = value;
  const output = h('output', { 'aria-live': 'polite' }, String(current));
  const minus = h('button', { type: 'button', 'aria-label': `Quitar ${label}`, onclick: () => set(current - 1) }, '−');
  const plus = h('button', { type: 'button', 'aria-label': `Añadir ${label}`, onclick: () => set(current + 1) }, '+');

  function set(next) {
    current = Math.max(min, Math.min(max, next));
    output.textContent = String(current);
    minus.disabled = current <= min;
    plus.disabled = current >= max;
    onChange(current);
  }

  minus.disabled = current <= min;
  plus.disabled = current >= max;
  return h('div', { class: 'stepper' }, minus, output, plus);
}
