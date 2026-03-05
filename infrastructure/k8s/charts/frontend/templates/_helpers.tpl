{{- define "frontend.name" -}}
frontend
{{- end -}}

{{- define "frontend.fullname" -}}
{{- printf "%s-%s" (include "frontend.name" .) .Release.Name -}}
{{- end -}}
