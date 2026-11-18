// @ts-check
// @ts-expect-error - Módulo servido vía CDN; TS no puede resolver la URL.
import Alpine from "https://cdn.jsdelivr.net/npm/alpinejs@3.14.8/dist/module.esm.js"
import { api, normalizeErrors, toast } from "./api.js"

/** @typedef {import("./api.js").ApiPayload} ApiPayload */
/** @typedef {{ reset_link: string | null }} ForgotPasswordResponse */

function createForgotPassword() {
	return {
		form: { email: "" },
		errors: {},
		busy: false,
		sent: false,
		resetLink: "",

		async submit() {
			this.busy = true
			this.errors = {}

			try {
				const data = /** @type {ForgotPasswordResponse} */ (
					await api("/auth/password/forgot", {
						method: "POST",
						body: JSON.stringify({ email: this.form.email }),
					})
				)

				this.resetLink = data?.reset_link ?? ""
				this.sent = true
			} catch (error) {
				const err = /** @type {ApiPayload} */ (error)

				if (err?.errors) {
					this.errors = normalizeErrors(err.errors)
				} else {
					toast(err?.message ?? err?.error ?? "Ocurrió un error inesperado")
				}
			} finally {
				this.busy = false
			}
		},

		reset() {
			this.sent = false
			this.resetLink = ""
			this.errors = {}
		},
	}
}

Alpine.data("forgotPassword", createForgotPassword)
Alpine.start()
