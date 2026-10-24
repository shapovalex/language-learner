# Azure contract examples for story 6.1

These fixtures are **synthetic documented-contract examples**, not responses captured
from a real Azure subscription. The catalog is deliberately mixed-locale so filtering
can be observed. The example names do not claim to represent today's regional catalog.
The adapter must fetch the current catalog; it must not embed this fixture.

The request paths, authentication header, SSML body and MP3 output header follow
[Microsoft's Text to speech REST reference](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/rest-text-to-speech)
and [REST quickstart](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/get-started-text-to-speech).
Schema checks must be compared with a sanitized real reply during implementation or
story 6.4's released-wheel acceptance. No real credential was used to create these files.

`preview.mp3` and `second-preview.mp3` are valid, short silent clips encoded locally with
PyAV/libmp3lame at 24 kHz mono (three and five frames of 1152 samples). They test binary
transport and byte preservation, without calling a paid service or containing user speech.
Neither is a real Azure TTS recording, and neither proves pronunciation or voice quality.

Anki `storeMediaFile`, `retrieveMediaFile`, `deleteMediaFile` replies in the test helper
are documented v6 shapes. They extend the existing collection replay with media bytes;
real Azure and Anki media reply comparisons remain pending acceptance evidence.
