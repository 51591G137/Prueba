/* La carta: plato ..... precio, con la descripción debajo.
   Con hrefFor, cada plato es un enlace (la app de restaurantes lo usa para editarlo). */
import { empty, h } from '../core/dom.js';
import { euro } from '../core/format.js';

export function menuList(items, emptyText, { hrefFor } = {}) {
  if (!items.length) return h('ul', { class: 'list' }, empty(emptyText));
  return h(
    'ul',
    { class: 'carta' },
    items.map((item) => {
      const content = [
        h(
          'div',
          { class: 'carta-line' },
          h('span', { class: 'dish' }, item.name),
          h('span', { class: 'leader', 'aria-hidden': 'true' }),
          h('span', { class: 'price' }, euro.format(item.price)),
        ),
        item.description && h('p', { class: 'desc' }, item.description),
      ];
      return hrefFor
        ? h('li', { class: 'editable' }, h('a', { href: hrefFor(item) }, content))
        : h('li', null, content);
    }),
  );
}
