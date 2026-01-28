{% test accepted_range(model, column_name, min_value=None, max_value=None) %}

select *
from {{ model }}
where {{ column_name }} is not null
  and (
    {% if min_value is not none %}
      {{ column_name }} < {{ min_value }}
    {% endif %}
    {% if min_value is not none and max_value is not none %}
      or
    {% endif %}
    {% if max_value is not none %}
      {{ column_name }} > {{ max_value }}
    {% endif %}
  )

{% endtest %}
