/** @odoo-module **/
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { registry } from "@web/core/registry";
const {Component} = owl;


export class IsProgressbar extends Component {
    setup() {
        super.setup();
    }
}
IsProgressbar.template = "is_plastigray16.IsProgressbar";
IsProgressbar.props = standardFieldProps;
registry.category("fields").add("is_progressbar", IsProgressbar);


