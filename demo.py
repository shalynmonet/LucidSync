"""An instant, explicitly synthetic dream record for the hackathon demo."""
from models import DreamRecord, DreamScene, DreamCharacter, DreamObject


def sample_dream():
    cat = DreamCharacter(id="character_1", name="white cat", visual_description="A small white cat with green eyes and a blue collar")
    return DreamRecord(
        dream_report="I walked through a blue garden with a small white cat with green eyes and a blue collar. A wooden bench stood beside a red door. The cat led me through the door into a glasshouse full of golden flowers. I felt curious, then peaceful.",
        mood_on_waking="peaceful", vividness=4,
        scenes=[
            DreamScene(scene_number=1,setting="A blue garden beside a red door",characters=[cat],objects=[DreamObject(id="object_1",name="wooden bench",visual_description="A wooden bench"),DreamObject(id="object_2",name="red door",visual_description="A red door")],actions=["I walk with the cat toward the door"],emotions=["curious"],colors=["blue","white","red"],vividness=4),
            DreamScene(scene_number=2,setting="A glasshouse full of golden flowers",characters=[cat.model_copy()],objects=[DreamObject(id="object_3",name="golden flowers",visual_description="Golden flowers inside the glasshouse")],actions=["The cat leads me into the glasshouse"],emotions=["peaceful"],colors=["gold","white"],vividness=4),
        ])
