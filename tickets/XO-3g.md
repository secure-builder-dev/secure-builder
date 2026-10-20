id: XO-3g
unit: XO-3
state: open
depends_on: -
done_when: CommentThread (default export of frontend/src/CommentThread.tsx, props comments and onAdd) renders div.comment-thread with an ol.comments named Comments holding one li.comment per comment (span.comment-author with the author, p.comment-body with the text), or p.empty with No comments yet when there are none; its form.comment-form has a textarea labelled Comment and an Add comment submit button — submitting calls onAdd with the stripped text and empties the field, and blank text calls nothing; HistoryList (default export of frontend/src/HistoryList.tsx, prop events) renders ol.history named History with one li per event, oldest first, reading 'her filed it', 'him moved it from open to acknowledged' (a status with _ shows a space, as in in progress) or 'her edited it', or p.empty with No history when there are none

# XO-3g
