/* Etiquetas de estado de las comandas y de las mesas. */
import { h } from '../core/dom.js';

export const ORDER_STATUS = {
  pedido: 'Pedido',
  en_preparacion: 'En preparación',
  listo_para_servir: 'Listo para servir',
  servido: 'Servido',
  cancelado: 'Cancelada',
};

export const orderChip = (status) => h('span', { class: `chip status-${status}` }, ORDER_STATUS[status] || status);

export const tableChip = (status) =>
  status === 'ocupada' ? h('span', { class: 'chip busy' }, 'Ocupada') : h('span', { class: 'chip free' }, 'Libre');
