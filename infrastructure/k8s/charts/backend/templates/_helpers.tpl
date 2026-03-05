{{- define "backend.name" -}}
backend
{{- end -}}

{{- define "backend.fullname" -}}
{{- printf "%s-%s" (include "backend.name" .) .Release.Name -}}
{{- end -}}

# © PUBLIUS33™ — PulseTrakAI™. All Rights Reserved.
