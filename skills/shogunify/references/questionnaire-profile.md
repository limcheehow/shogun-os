# Questionnaire — New Department Profile

Use when adding a Hermes department agent (not a skill/connector alone).

Prefer existing tooling: `python3 ~/shogun-os/scripts/generate-profile.py <name> --type <type>`.

## Questions

1. **Profile slug?** (`warehouse-manager`)  
2. **Type?** must be in `generate-profile.py` PROFILE_META or add new type  
3. **Persona name + kanji/theme?**  
4. **Gbrain source id + path?** (`gbrain sources add …`)  
5. **Gateway port?** align with web portal map if UI-exposed  
6. **Skills to link at create?** always include `company-workflow`, `shogunify`, plus domain skills  
7. **Scrum?** yes → wire department-scrum crons  
8. **Provider abstraction?** which recipe domain  
9. **Slack/Telegram bot?** separate tokens vs main gateway routing  
10. **Industry pack?** general | manufacturing | retail  

## Generation order

1. `gbrain sources add <src> --path ~/brain/<src>`  
2. `hermes profile create <slug>` if needed  
3. `python3 scripts/generate-profile.py <slug> --type <type>`  
4. `python3 scripts/wire-crons.py <slug> --type <type> --apply`  
5. Profile `.env` keys + Slack tokens  
6. `install-to-profiles.py --skill shogunify --profiles <slug>`  
7. Update PROFILE_CATALOG.md + web portal dept map if public  

## Done when

- [ ] Profile dir exists with SOUL + config  
- [ ] Skills linked including shogunify  
- [ ] Gbrain whoami / source works  
- [ ] Crons listed if scrum  
- [ ] Catalog updated  
