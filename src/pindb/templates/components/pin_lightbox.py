"""
htpy page and fragment builders: `templates/components/pin_lightbox.py`.

Single full-screen image viewer with zoom (wheel, +/- buttons, pinch),
pan, ESC/click-out/X close, focus trap, and reduced-motion safe transform.
Triggered by clicking any element with the ``pin-zoomable`` class.
The init script moves the overlay to ``document.body`` so it escapes any
ancestor stacking context (e.g. ``main``). Logic lives in ``templates/js/pin_lightbox.js``.
"""

from htpy import Element, button, div, i, img, span


def pin_lightbox() -> Element:
    btn_cls = (
        "p-2 rounded-lg bg-main hover:bg-lighter-hover "
        "border border-lightest text-base-text"
    )
    return div(
        id="pin-lightbox",
        class_="hidden fixed inset-0 z-50 items-center justify-center bg-darker/80",
        role="dialog",
        aria_modal="true",
        aria_label="Pin image — full size",
        tabindex="-1",
    )[
        img(
            id="pin-lightbox-img",
            alt="",
            draggable="false",
            class_=(
                "max-w-[95vw] max-h-[95vh] object-contain select-none "
                "touch-none will-change-transform"
            ),
            style="transform-origin: center center; transition: transform 60ms ease-out;",
        ),
        div(class_="absolute top-2 right-2 flex gap-1")[
            button(
                type="button",
                id="pin-lightbox-zoom-out",
                aria_label="Zoom out",
                class_=btn_cls,
            )[i(data_lucide="zoom-out", class_="w-5 h-5", aria_hidden="true")],
            button(
                type="button",
                id="pin-lightbox-zoom-in",
                aria_label="Zoom in",
                class_=btn_cls,
            )[i(data_lucide="zoom-in", class_="w-5 h-5", aria_hidden="true")],
            button(
                type="button",
                id="pin-lightbox-close",
                aria_label="Close",
                class_=btn_cls,
            )[i(data_lucide="x", class_="w-5 h-5", aria_hidden="true")],
        ],
        span(
            id="pin-lightbox-zoom-label",
            class_=(
                "absolute bottom-3 left-1/2 -translate-x-1/2 text-white text-sm "
                "bg-darker px-2 py-0.5 rounded"
            ),
            aria_live="polite",
        )["100%"],
    ]
