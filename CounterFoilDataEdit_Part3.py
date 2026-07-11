import db_credentials
from datetime import datetime


class CounterFoilDataEditPart3Mixin:

    # =====================================================
    # ERROR LOGGING
    # =====================================================

    def log_error(
        self,
        screen,
        module,
        error_text
    ):

        try:

            conn = db_credentials.get_sql_connection()

            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO ErrorLog
                (
                    ErrorScreen,
                    ErrorModule,
                    ErrorText,
                    ErrorTime
                )
                VALUES
                (
                    ?, ?, ?, GETDATE()
                )
                """,
                (
                    screen,
                    module,
                    str(error_text)
                )
            )

            conn.commit()

            cursor.close()
            conn.close()

        except:
            pass

    # =====================================================
    # YES / NO TO BIT
    # =====================================================

    def yes_no_to_bit(self, value):

        if str(value).strip().upper() == "YES":
            return 1

        return 0

    # =====================================================
    # UPDATE
    # =====================================================

    def update_record(self):

        try:

            id_text = self.lbl_id.cget("text")

            if ":" not in id_text:
                self.message_var.set(
                    "Please select a record."
                )
                return

            record_id = int(
                id_text.split(":")[1].strip()
            )

            conn = db_credentials.get_sql_connection()

            cursor = conn.cursor()

            cursor.execute(
                """
                EXEC usp_CounterFoilEditUpdate
                     @EditFor=?,
                     @UserID=?,
                     @ID=?,
                     @barcode=?,
                     @bubble_regno=?,
                     @handwritten_regno=?,
                     @subject_code=?,
                     @BookletSlNo=?,
                     @CandSig=?,
                     @InvSign=?,
                     @WhitenerDesc=?,
                     @isBlackDesc=?,
                     @ThDesc=?
                """,
                (
                    self.edit_for_var.get(),
                    self.user_id,
                    record_id,

                    self.editor_vars[
                        "barcode_var"
                    ].get(),

                    self.editor_vars[
                        "bubble_var"
                    ].get(),

                    self.editor_vars[
                        "hand_var"
                    ].get(),

                    self.editor_vars[
                        "subject_code_var"
                    ].get(),

                    self.editor_vars[
                        "booklet_var"
                    ].get(),

                    self.yes_no_to_bit(
                        self.editor_vars[
                            "candsig"
                        ].get()
                    ),

                    self.yes_no_to_bit(
                        self.editor_vars[
                            "invsig"
                        ].get()
                    ),

                    self.yes_no_to_bit(
                        self.editor_vars[
                            "whitener"
                        ].get()
                    ),

                    self.yes_no_to_bit(
                        self.editor_vars[
                            "nonstd"
                        ].get()
                    ),

                    self.yes_no_to_bit(
                        self.editor_vars[
                            "threshold"
                        ].get()
                    )
                )
            )

            conn.commit()

            cursor.close()
            conn.close()

            self.message_var.set(
                "Record updated successfully."
            )

            self.load_data()

        except Exception as ex:

            self.log_error(
                "CounterFoilDataEdit",
                "Update",
                ex
            )

            self.message_var.set(
                str(ex)
            )

    # =====================================================
    # SKIP
    # =====================================================

    def skip_record(self):

        try:

            id_text = self.lbl_id.cget(
                "text"
            )

            if ":" not in id_text:

                self.message_var.set(
                    "Please select a record."
                )

                return

            record_id = int(
                id_text.split(":")[1].strip()
            )

            conn = db_credentials.get_sql_connection()

            cursor = conn.cursor()

            cursor.execute(
                """
                EXEC usp_CounterFoilEditSkip
                     @EditFor=?,
                     @UserID=?,
                     @ID=?
                """,
                (
                    self.edit_for_var.get(),
                    self.user_id,
                    record_id
                )
            )

            conn.commit()

            cursor.close()
            conn.close()

            self.message_var.set(
                "Record skipped successfully."
            )

            self.load_data()

        except Exception as ex:

            self.log_error(
                "CounterFoilDataEdit",
                "Skip",
                ex
            )

            self.message_var.set(
                str(ex)
            )

    # =====================================================
    # GOTO ROW
    # =====================================================

    def goto_row(self):

        try:

            row_no = int(
                self.goto_row_var.get()
            )

            if row_no <= 0:

                return

            self.current_page = (
                ((row_no - 1)
                // self.PAGE_SIZE)
                + 1
            )

            if self.current_page > self.total_pages:

                self.current_page = (
                    self.total_pages
                )

            self.bind_page()

        except:

            self.message_var.set(
                "Invalid Row Number."
            )

    # =====================================================
    # VALIDATION
    # =====================================================

    def validate_7_digit(self, value):

        if value == "":
            return True

        if not value.isdigit():
            return False

        if len(value) > 7:
            return False

        return True

    def validate_filename(
        self,
        value
    ):

        if len(value) > 200:
            return False

        return True

    # =====================================================
    # REGISTER VALIDATION
    # =====================================================

    def register_validators(self):

        v1 = (
            self.root.register(
                self.validate_7_digit
            ),
            "%P"
        )

        v2 = (
            self.root.register(
                self.validate_filename
            ),
            "%P"
        )

        self.txt_fromsheet.config(
            validate="key",
            validatecommand=v1
        )

        self.txt_tosheet.config(
            validate="key",
            validatecommand=v1
        )

        self.txt_sheetno.config(
            validate="key",
            validatecommand=v1
        )

        self.txt_filename.config(
            validate="key",
            validatecommand=v2
        )

    # =====================================================
    # REFRESH CURRENT ROW
    # =====================================================

    def refresh_current_row(self):

        selected = self.tree.selection()

        if not selected:
            return

        self.grid_row_selected()

    # =====================================================
    # BUTTON WIRING
    # =====================================================

    def wire_buttons(self):

        self.btn_update.configure(
            command=self.update_record
        )

        self.btn_skip.configure(
            command=self.skip_record
        )

        self.btn_goto.configure(
            command=self.goto_row
        )
    
    
