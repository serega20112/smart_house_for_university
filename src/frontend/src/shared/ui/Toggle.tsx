import "./toggle.css";
/**
 * Тумблер: один признак, два состояния.
 *
 * Клик по любому месту переключателя меняет признак, а не только по попалки; подписью
 * служит тот текст, рядом с которым тумблер стоит, поэтому лишняя подпись в разметке
 * не нужна.
 */

interface ToggleProps {
  checked: boolean;
  disabled?: boolean;
  label: string;
  onChange: (next: boolean) => void;
}

/**
 * Возвращает доступный переключатель.
 *
 * @param props.checked Включён ли признак сейчас.
 * @param props.disabled Запрет менять: действие занято или недоступно.
 * @param props.label Что переключатель значит, для программ чтения с экрана.
 * @param props.onChange Вызывается с новым значением.
 * @returns Разметка тумблера.
 */
export function Toggle({ checked, disabled, label, onChange }: ToggleProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      className={`toggle ${checked ? "toggle--on" : ""}`.trim()}
      disabled={disabled}
      onClick={() => onChange(!checked)}
    >
      <span className="toggle__knob" />
    </button>
  );
}
