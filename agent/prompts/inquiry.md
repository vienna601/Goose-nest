# Inquiry message template

Plain text. No markdown in the actual send — landlord inboxes and web forms
render it as-is.

Keep it short. A wall of text from a stranger reads as a scam, and student
housing has a lot of scams in it (Bamboo ships a whole /avoidrentscams page).

---

Hi{% if contact_name %} {{ contact_name }}{% endif %},

I'm interested in {{ listing_label }}{% if price %} listed at ${{ price }}/month{% endif %}.

{{ availability_line }}

{% if questions %}A couple of questions:
{% for q in questions %}- {{ q }}
{% endfor %}{% endif %}
Is it still available? I'm happy to arrange a viewing.

Thanks,
{{ sender_name }}
{{ sender_email }}{% if sender_phone %}
{{ sender_phone }}{% endif %}

---

## Rules

- Never invent details about the sender. If we don't have a phone number, the
  message has no phone number.
- Never claim to be a student at a specific school, or to have a guarantor, or
  anything else we weren't told. The agent fills a form; it does not negotiate.
- One message per listing. `EmailsSent` on the Bamboo payload is a reminder
  that landlords see volume.
