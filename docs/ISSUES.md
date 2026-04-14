# Issues to Fix

## 1. Empty link creation.
When creating links, it is possible to create empty links. This should not be possible. It should be caught in the validation layer and empty links ignored.

## 2. Editors should be able to make pending edits.
Editors currently can only make new entries, or edit entries they own. They should have the ability to edit entries they do not own, and those edits will enter a pending state. For example, if an editor edits Pin A, then there is a Pending version of Pin A, and the canonical version of Pin A. Until an administrator approves the edit, the canonical version is shown to the average user, and the pending version is shown to editors and admins.

## 3. Contextual Back button
On pin page, there is a back button that uses browser history. This is not always desirable, eg, if you click on it after editing the pin, it sends you back into editing the pin. What is more desirable is linking back to wherever you entered the pin from originally, regardless of navigation past that. EG, if I were to enter the pin through a pin set, then edit the pin, then click "back", I want to go back to the pin set. My initial thought about how to do that is to either capture something in headers or query params.

## 4. Bulk Pin changes
The copy/paste functionality does not work as expected with tom select multi selects. Copying a TS field and pasting pastes nothing, and clears the pasted field.
Most fields do not copy/paste correctly, except for basic input fields.
When creating a new tag/pin set/etc in the bulk page, by using the tom select "add" feature, that newly added name should be available when searching in the same type of field. EG. If I add a tag "red" in row 1, then in row 2 if I search "red", it should appear as an option, even if it doesn't actually exist in the DB yet.
The name column should expand to the largest name, and float left/sticky on horizontal scroll so it is always visible.