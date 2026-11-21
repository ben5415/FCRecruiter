import { useState } from "react";

import type { Role } from "../api/auth";

const ROLE_OPTIONS: Array<{ value: Role; label: string }> = [
  { value: "manager", label: "Manager" },
  { value: "player", label: "Player" },
  { value: "doctor", label: "Doctor" },
  { value: "coach", label: "Coach" },
];

export function RolePicker({ value, onChange }: { value: Role; onChange: (role: Role) => void }) {
  const [open, setOpen] = useState(false);
  const currentLabel = ROLE_OPTIONS.find((option) => option.value === value)?.label ?? value;

  return <div className="role-picker">
    <button
      aria-expanded={open}
      aria-haspopup="listbox"
      className={open ? "role-picker__control role-picker__control--open" : "role-picker__control"}
      type="button"
      onBlur={() => setTimeout(() => setOpen(false), 100)}
      onClick={() => setOpen((current) => !current)}
    >
      <span>{currentLabel}</span>
      <svg aria-hidden="true" viewBox="0 0 20 20"><path d="m5 7.5 5 5 5-5" /></svg>
    </button>
    {open && <div className="club-picker__menu" role="listbox">
      {ROLE_OPTIONS.map((option) => <button
        aria-selected={option.value === value}
        className={option.value === value ? "club-picker__option club-picker__option--selected" : "club-picker__option"}
        key={option.value}
        role="option"
        type="button"
        onMouseDown={(event) => event.preventDefault()}
        onClick={() => { onChange(option.value); setOpen(false); }}
      >{option.label}</button>)}
    </div>}
  </div>;
}
