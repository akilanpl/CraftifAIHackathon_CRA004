# Apply the original PipeGen evidence to the CURRENT GitHub README

Repository: https://github.com/akilanpl/CraftifAIHackathon_CRA004

The bundle includes a full README_updated_reference.md draft, three original PipeGen screenshots, three readable crops, and a safe patch script.

IMPORTANT: The repository's current README may be newer than the prepared full draft.
The recommended method below preserves every other section of the latest checked-out README.

1. Open the repository on your computer, or clone it:

   git clone https://github.com/akilanpl/CraftifAIHackathon_CRA004.git
   cd CraftifAIHackathon_CRA004

2. Extract the ZIP into the repository root. Ensure `evidence/pipegen-gui/` contains all six PNG files.
   The bundle's README_updated_reference.md is a standalone reference: do not overwrite your existing README with it unless you specifically want to replace the whole document.

3. From the repo root run:

   python3 apply_to_current_readme.py

4. Preview locally and confirm the graph, speed report and Run summary images render, with each crop opening its original screenshot.

5. Publish only the intended evidence assets and updated README, retaining other repo files:

   git fetch origin main
   git add README.md evidence/pipegen-gui/
   git diff --cached --stat
   git -c user.name=Akilan -c user.email=248480019+akilanpl@users.noreply.github.com commit -m 'Add original PipeGen graph, benchmark and run screenshots'
   git push origin main

If others have advanced main, do not force-push. Reconcile their changes first. There is no need to rerun PipeGen.

The DeepStream screenshot is the original actual PipeGen Run page. The embedded crop shows a finished 254-frame warehouse run, not a claim that a new run was performed when this README was updated.
