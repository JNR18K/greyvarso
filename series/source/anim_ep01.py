# Plans 3D animés de l'épisode 1 (un par scène, même ordre que le script)
LOOKS = {
    "lea": {"hairStyle": "long", "hair": "#f0c060", "dress": "#ffd43b", "shirt": "#ffd43b", "skin": "#f6d2b0"},
    "client": {"robe": True, "hairStyle": "bald", "hair": "#c8c8c8", "glasses": True, "chubby": True, "skin": "#efc29a"},
    "efraim": {"chubby": True, "hairStyle": "curly", "hair": "#1f1410", "beard": True, "aviators": True, "chain": True,
               "shirt": "#f4f4f4", "pants": "#f4f4f4", "shoes": "#ffffff"},
}
ANIM = [
  {"set": "warehouse", "camera": {"from": [0, 1.6, 2], "to": [0, 1.6, -2.5], "look": [0, 1.4, -12], "walk": True}, "handPose": "idle"},
  {"set": "crate_open", "camera": {"from": [0, 1.75, 0.7], "to": [0, 1.25, -0.5], "look": [0, 0.25, -1.2]}, "handPose": "low"},
  {"set": "warehouse", "camera": {"from": [0, 1.5, 0.5], "look": [0, 1.2, -3], "shake": 0.7}, "handPose": "phone", "handShake": 1.5,
   "phone": ["Efraim", "", "appel…", "00:03"]},
  {"set": "miami", "camera": {"from": [-3.6, 1.6, 6], "to": [-3.6, 1.6, -3], "look": [-3.2, 2.3, -30], "walk": True}, "handPose": "idle"},
  {"set": "spa", "camera": {"from": [0.7, 1.6, 1.3], "to": [0.25, 1.6, 0.6], "look": [0, 1.15, -1.6]}, "handPose": "hold",
   "actors": [{"id": "client", "pos": [0, 0.31, -2.0], "act": {"action": "sit", "mood": "neutral"}}]},
  {"set": "spa", "camera": {"from": [0, 1.55, 0.3], "to": [0, 1.5, 0.0], "look": [0, 0.95, -1.4]}, "handPose": "low",
   "coins": True, "coinsAt": 0.9, "coinsPos": [0.05, 0.85, -0.95],
   "actors": [{"id": "client", "pos": [0, 0.31, -2.0], "act": {"action": "toss", "at": 0.5, "mood": "neutral"}}]},
  {"set": "spa", "camera": {"from": [0, 1.5, -0.55], "to": [0, 1.52, -0.9], "look": [0, 1.5, -2.0]}, "handPose": "low",
   "actors": [{"id": "client", "pos": [0, 0.31, -2.0], "act": {"action": "point", "mood": "angry"}}]},
  {"set": "spa", "camera": {"from": [0, 1.55, 0.6], "to": [0, 1.5, 0.45], "look": [0, 1.0, -0.6]}, "handPose": "palms"},
  {"set": "apartment_night", "camera": {"from": [0, 1.55, 0.2], "to": [0, 1.35, -0.35], "look": [0, 0.8, -1.0]}, "handPose": "table"},
  {"set": "memory", "camera": {"from": [-0.2, 1.22, -0.05], "to": [-0.2, 1.12, -0.55], "look": [-0.2, 1.08, -1.05]}, "handPose": "low"},
  {"set": "living", "camera": {"from": [0, 1.5, 0.6], "to": [0, 1.45, 0.0], "look": [0.2, 1.05, -2.2]}, "handPose": "idle",
   "actors": [{"id": "lea", "pos": [0.2, 0.15, -2.2], "act": {"action": "sit", "mood": "happy"}}]},
  {"set": "balcony", "camera": {"from": [0, 1.55, 0.7], "to": [-0.1, 1.55, 0.4], "look": [0.5, 1.5, -2.5]}, "handPose": "low",
   "actors": [{"id": "lea", "pos": [0.75, 0, -1.9], "rotY": -0.35, "act": {"mood": "happy", "action": "hug_self"}}]},
  {"set": "laptop", "camera": {"from": [0, 1.32, 0.15], "to": [0, 1.12, -0.45], "look": [0, 1.0, -1.15]}, "handPose": "table"},
]
