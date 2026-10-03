function uniquePermutationCount(value) {
  const counts = new Map();
  for (const digit of value) counts.set(digit, (counts.get(digit) || 0) + 1);
  const factorial = [1, 1, 2, 6, 24];
  let result = factorial[value.length];
  for (const count of counts.values()) result /= factorial[count];
  return result;
}

const form = typeof document === 'undefined' ? null : document.querySelector('#practice-form');
const numberInput = typeof document === 'undefined' ? null : document.querySelector('#practice-number');
const result = typeof document === 'undefined' ? null : document.querySelector('#practice-result');

numberInput?.addEventListener('input', () => {
  numberInput.value = numberInput.value.replace(/\D/g, '').slice(0, 4);
});

form?.addEventListener('submit', event => {
  event.preventDefault();
  const data = new FormData(form);
  const number = String(data.get('number') || '');
  const amount = Number(data.get('amount'));
  result.hidden = false;

  if (!/^\d{4}$/.test(number) || !Number.isInteger(amount) || amount < 1 || amount > 999) {
    result.innerHTML = '<p class="error"><strong>Check the example:</strong> enter exactly four digits and a whole RM amount from 1 to 999.</p>';
    return;
  }

  const provider = String(data.get('provider'));
  const type = String(data.get('type'));
  const pool = String(data.get('pool'));
  const permutations = uniquePermutationCount(number);
  const playLabel = type === 'ibox' ? `IBOX / i-Perm (${permutations} unique arrangements)` : 'Straight (one exact order)';

  result.innerHTML = `<p><strong>Example slip</strong></p><p>${provider} · ${number} · ${playLabel} · ${pool} · RM${amount.toFixed(2)}</p><p>This is a practice summary only. Confirm product availability, cost and current rules with the provider before making any real purchase.</p>`;
});

export { uniquePermutationCount };
