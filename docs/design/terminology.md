# Terminology

## Transcription vs Alignment

**Transcription** (word-level text):
- What was said (words)
- Input data for training
- Format: `<fileid> <word1> <word2> ...`
- Example: `arctic_a0001 hello world`
- No timing information

**Alignment** (time-aligned boundaries):
- When each phone/word occurs (frame boundaries)
- Output data from training/decoding
- Format: Phone segmentation files (`.phseg`) with start/end frames
- Example: Phone `HH` from frame 10 to 15, phone `AH` from frame 16 to 20
- Includes timing information

## Usage

- **Transcriptions** are used as input to training (what words to expect)
- **Alignments** are optional outputs from training (where phones occur in time)
- Use `--save-alignments` to save alignments during CI training
