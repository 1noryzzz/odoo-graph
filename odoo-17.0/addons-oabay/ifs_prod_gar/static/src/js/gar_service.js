/** @odoo-module alias=ifs.prod.gar.service **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

var tour = require('web_tour.tour');

// const effectService = useService("effect");

const myService = {
  dependencies: ["notification"],
  start(env, { notification }) {
    // let counter = 1;
    // setInterval(() => {
    //   notification.add(`Tick Tock ${counter++}`);
    // }, 5000);

    setTimeout(() => {
      try {
        const effectService = useService("effect");
        effectService.add({
          type: "rainbow_man",
          message: "欢迎回来！",
        });
      } catch (err) { }
    }, 2000)

    // const effectService = useService("effect");

    // effectService.add({
    //     type: "rainbow_man",
    //     message: "Boom! Team record for the past 30 days.",
    // });

    // tour.register('project_tour', {
    //   sequence: 110,
    //   url: "/web",
    //   rainbowManMessage: "Congratulations, you are now a master of project management.",
    // });

    // this.start_tour("/web", 'project_tour')
  }
};

registry.category("services").add("myService", myService);

export default myService;
