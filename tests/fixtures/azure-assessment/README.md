# Azure Assessment fixtures — story 7.2

Copied byte for byte from the real 2026-10-25 Azure REST probe under
`_bmad-output/initiative-languagelab-v1/epic-pronunciation-review/research-azure-assessment/`.
`manifest.json` records each source path and SHA-256. No credentials or account data occur
in these raw responses. Test transports replay them offline; no test calls Azure or Anki.

- `en-weather.mp4-aac.mp4` and `en-weather.webm-opus.webm`: the probe's PyAV encodings
  of “What's the weather like?”, `whatstheweatherlike.wav` from
  Azure-Samples/cognitive-services-speech-sdk, **MIT**, as documented in the probe findings.
  These exercise the same AAC/MP4 and Opus/WebM codecs as MediaRecorder, not a real
  iPhone recording; device acceptance is story 7.4.
- `single-en-US-taught-vs-thought.json`: raw REST result for Azure TTS Andrew saying
  “taught” against the reference “thought”; flat NBest scores, IPA and prosody.
- `single-fr-CA-bonsoir-vs-bonjour.json`: raw result for Azure TTS Sylvie saying
  “bonsoir” against “bonjour”; empty phoneme labels, ordered scores [100,17,0,0,0].
- `silence-enUS.json`: HTTP 200 Success for silence against “What's the weather like?”;
  every word Omission. It is not an HTTP/provider failure.

The two single-word inputs were synthesized with the project subscription in the probe.
Their responses are provider output, copied unmodified; the original MP3s remain with the
probe because adapter normalization consumes a known WAV and only needs these responses.

The tests propose a shared Assessment wire shape with `locale`, `overall`, `accuracy`,
`fluency`, `completeness`, nullable `prosody` and `words`. A word carries `text`, `score`,
`errorType`, `phonemes` (`symbol`, `score`) and nullable `positions`. French has no
phonemes or prosody. For positions the explicit scaffold choice is bucket
`min(2, floor(3*i/n))` for index i among n phonemes, with the minimum score per bucket.
The five-phoneme fixture becomes start=17, middle=0, end=0. The product documents require
positions but leave this aggregation unspecified; builders may amend this one choice.
