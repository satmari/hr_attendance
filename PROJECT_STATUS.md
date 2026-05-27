# PROJECT STATUS

## Sta je uradjeno

Napravljen je Django sistem za rad sa HR Excel fajlom koji koristi veliki `main` sheet i monthly split model.

Postoje moduli:
- landing
- import
- Pregled unosa
- edit zaposlenog

## Poslovna logika

Importer ocekuje:
- sheet `main`
- period u redu 5
- header u redu 6
- podatke od reda 7

Glavna tabela:
- `personnel_presence`

Child tabele:
- `personnel_presence_department`
- `personnel_presence_location`
- `personnel_presence_shift`
- `personnel_presence_inteos`
- `personnel_presence_zucchetti`

Kljuc:
- `employee_code + month + year`

## Sledeci logican nastavak

- povezivanje na MSSQL
- potvrda finalnog mapiranja kolona
- UI dugme za brisanje po mesecu i godini
- eventualni export nazad u Excel
