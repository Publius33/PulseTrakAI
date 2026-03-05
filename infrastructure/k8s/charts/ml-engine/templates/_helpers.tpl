{{- define "ml-engine.name" -}}
ml-engine
{{- end -}}

{{- define "ml-engine.fullname" -}}
{{- printf "%s-%s" (include "ml-engine.name" .) .Release.Name -}}
{{- end -}}

# © PUBLIUS33™ — PulseTrakAI™. All Rights Reserved.
