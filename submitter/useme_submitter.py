"""Submits an offer on Useme using a saved login session (see
scripts/save_session.py — we never automate the login itself, only reuse a
session you created by logging in manually).

TODO (Oleh): implement submit_offer(). This is a Playwright script, similar
in spirit to browser automation you've already used in the SYNTHETIKA / other
scraping work — except here you're *filling and submitting a form* instead of
just reading a page.

--- What the page looks like (already inspected in the browser) ---

1. Start at the job URL, e.g. https://useme.com/en/jobs/<slug>,<id>/
   Click the "Add an offer" button (or navigate straight to the offer URL —
   check what it redirects to; it was something like a "Post a job offer"
   page with a form).

2. On that page, the fields you need to fill:
   - Description: NOT a plain <textarea>. It's a rich-text editor —
     a <div contenteditable="true"> — and there's a hidden
     <input id="id_description"> that the editor syncs into automatically.
     So: click the contenteditable div, then type the offer text into it
     (Playwright's `.click()` + `.type()` on the contenteditable element,
     not `.fill()` — fill() only works on real <input>/<textarea>).
   - Copyright: three radio buttons, name="copyright_transfer",
     ids id_copyright_transfer_0/1/2. You'll need to check which id
     corresponds to which label ("License" / "Copyright transfer" /
     "No copyright transfer") — don't hardcode blindly, read the label
     text next to each radio at runtime, or inspect once by hand and note
     it in a comment. Pick "No copyright transfer" for translation-type gigs
     unless a listing's description says otherwise.
   - Price: <input id="id_payment"> — plain text input, use `.fill(str(amount))`.
   - Currency: <select id="id_currency"> — it's "selectized" (a JS widget
     wrapping a real <select>), so a plain `.select_option()` on the
     underlying <select> should still work since Playwright operates on the
     DOM element directly, bypassing the UI widget.
   - Workdays: <input id="id_work_days"> — plain text input, minimum 7.

3. Submit button: "Go to summary" — this is a two-step wizard. After
   clicking it, you land on a Summary page with a final send/confirm button
   (its exact label wasn't inspected yet — check when you get there).

--- Function signature to implement ---

def submit_offer(job_id: str, job_url: str, offer_text: str, price: int = 0,
                  currency: str = "PLN", workdays: int = 7) -> None:
    '''Fills and submits the offer form for a Useme job.

    Raises an exception on any failure (missing session file, form fields not
    found, submission not confirmed) — telegram_bot.py already wraps calls to
    this function in try/except and reports failures back to Oleh, so don't
    swallow errors here.
    '''
    # 1. Load storage_state.json (fail loudly with a clear message if it's
    #    missing — that means the session needs to be refreshed via
    #    scripts/save_session.py).
    # 2. Launch Playwright (headless=True is fine here — you're not solving
    #    any bot challenge, just replaying an authenticated session).
    # 3. new_context(storage_state="storage_state.json")
    # 4. Navigate, click "Add an offer", fill the fields described above.
    # 5. Click through to the summary page and confirm.
    # 6. Close the browser. Raise on any unexpected state (e.g. still seeing
    #    the login page = session expired).
    raise NotImplementedError("TODO: Oleh implements this")
