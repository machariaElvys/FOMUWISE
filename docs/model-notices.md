# Model and data notices

## Gemma 4

The default model is `gemma-4-26b-a4b-it`, served through the Gemini API. The model can be changed with `GEMMA_MODEL`. Google lists Gemma 4 under the Apache 2.0 license; check the current model card and terms before changing how or where a model is served.

- [Official Gemma 4 model card](https://ai.google.dev/gemma/docs/core/model_card_4)
- [Gemma models with the Gemini API](https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api)
- [Gemini generateContent API](https://ai.google.dev/api/generate-content)

## Data flow

1. The API receives a PDF and extracts selectable text page by page. Scanned-image PDFs are rejected; OCR is not included.
2. The original PDF is written to a uniquely named temporary file for extraction and removed in a `finally` cleanup step.
3. Extracted page text is sent to Google's Gemini API using Gemma 4 for analysis and, when asked, question answering. Do not upload sensitive material unless you have permission and have reviewed applicable provider terms.
4. The API validates quoted evidence against the relevant source page before returning generated claims.
5. Extracted text and the generated analysis are stored in the configured SQL database for up to 12 hours. A random bearer token is returned once; only its SHA-256 digest is persisted. The browser keeps the token in session storage to restore the workspace during the session.
6. Users may delete a workspace. Expired workspaces are removed during upload and when accessed after expiry.

FomuWise is an aid for understanding notices. It does not determine eligibility, submit applications, or replace confirmation from the issuing organisation.
