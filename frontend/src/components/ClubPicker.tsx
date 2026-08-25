import { useEffect, useState } from "react";

import type { ClubOption } from "../api/admin";

interface ClubPickerProps {
  clubs: ClubOption[];
  value: number;
  onChange: (clubId: number) => void;
  label: string;
  required?: boolean;
}

export function ClubPicker({ clubs, value, onChange, label, required = false }: ClubPickerProps) {
  const selectedName = clubs.find((club) => club.club_team_id === value)?.club_name ?? "";
  const [query, setQuery] = useState(selectedName);
  const [open, setOpen] = useState(false);
  const filteredClubs = clubs.filter((club) =>
    club.club_name.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()),
  );

  useEffect(() => setQuery(selectedName), [selectedName]);

  function handleInput(nextQuery: string) {
    setQuery(nextQuery);
    setOpen(true);
  }

  function selectClub(club: ClubOption) {
    setQuery(club.club_name);
    setOpen(false);
    if (club.club_team_id !== value) onChange(club.club_team_id);
  }

  return <div className="club-picker">
    <div className="club-picker__control">
      <input
        aria-label={label}
        aria-expanded={open}
        aria-autocomplete="list"
        autoComplete="off"
        placeholder="Type to search clubs"
        required={required}
        role="combobox"
        value={query}
        onChange={(event) => handleInput(event.target.value)}
        onFocus={() => setOpen(true)}
        onBlur={() => { setTimeout(() => setOpen(false), 100); setQuery(selectedName); }}
      />
      <button
        aria-label={`Show ${label} options`}
        className="club-picker__toggle"
        type="button"
        onMouseDown={(event) => event.preventDefault()}
        onClick={() => setOpen((current) => !current)}
      >⌄</button>
    </div>
    {open && <div className="club-picker__menu" role="listbox">
      {filteredClubs.length > 0 ? filteredClubs.map((club) =>
        <button
          className={club.club_team_id === value ? "club-picker__option club-picker__option--selected" : "club-picker__option"}
          aria-selected={club.club_team_id === value}
          key={club.club_team_id}
          role="option"
          type="button"
          onMouseDown={(event) => event.preventDefault()}
          onClick={() => selectClub(club)}
        >{club.club_name}</button>,
      ) : <p className="club-picker__empty">No clubs found</p>}
    </div>}
  </div>;
}
