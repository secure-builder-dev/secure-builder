id: GV-2h
unit: GV-2
state: claimed
depends_on: GV-2f, GV-2g
done_when: frontend/src/api.ts also exports fetchMe(token), which sends GET /api/me like the other calls and returns {user}, throwing Error(String(status)) when the answer is not ok; Load in frontend/src/App.tsx also calls fetchMe — once it has answered {user: 'her'} or {user: 'him'}, the header shows <span className="whoami">Signed in as {user}</span> after the token form, and the New ticket heading reads New ticket for him when the caller is her and New ticket for her when the caller is him; before /api/me has answered, or when it fails or answers anything else, there is no whoami element, the heading reads New ticket, no error message is shown for it, and the rest of the page works as before

# GV-2h
