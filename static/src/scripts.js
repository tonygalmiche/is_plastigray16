/** @odoo-module **/
const {Component} = owl;
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { registry } from "@web/core/registry";


export class PgColor extends Component {
    setup() {
        console.log("### TEST PgColor ###");
        super.setup();
    }
}
PgColor.template = "is_plastigray16.PgColor";
PgColor.props = standardFieldProps;
registry.category("fields").add("pgcolor", PgColor);



